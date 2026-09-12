"""chat 路由。

POST /chat：完整对话闭环
    ① 召回三层记忆 → 组装提示（人设 + 世界书 + 记忆 + 历史 + 本次输入）
    ② LLM 生成回复（默认 mock，无 key 也可跑通）
    ③ 回复后事件驱动写入：抽取事实 → 向量入库 → 摘要增量并入（参照③④）
    ④ 会话历史追加 user/assistant 两轮
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm.base import ChatMessage, LLMProvider
from app.llm.factory import create_llm_provider
from app.memory.cold.extractor import create_extractor
from app.memory.cold.sqlite_store import SqliteColdStore
from app.memory.store import MemoryStore
from app.memory.warm.factory import create_warm_store
from app.prompts.persona.loader import load_builtin_presets
from app.prompts.pipeline import assemble_chat
from app.session.context import ChatTurn
from app.session.repository import SessionRepository
from app.worldbook.loader import load_builtin_entries

router = APIRouter(prefix="/chat", tags=["chat"])

# 进程内单例（内存存储；后续里程碑替换为持久化/独立热层）
_repository = SessionRepository()
_presets = load_builtin_presets()
_entries = load_builtin_entries()
_memory_store: MemoryStore | None = None
_llm_provider: LLMProvider | None = None

_DEFAULT_PERSONA_ID = "therapist-elder-sister"


def get_memory_store() -> MemoryStore:
    """懒加载记忆门面（按配置创建冷/温层与抽取器）。

    冷层：SQLite（按陪伴对象分表）；温层：memory（默认零依赖）或 qdrant。
    测试可通过 set_memory_store 注入隔离实现。
    """
    global _memory_store
    if _memory_store is None:
        settings = get_settings()
        cold = SqliteColdStore(db_path=settings.cold_db_path)
        warm = create_warm_store(
            settings.warm_backend,
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        _memory_store = MemoryStore(
            cold,
            warm,
            fact_limit=settings.memory_fact_limit,
            memory_top_k=settings.memory_top_k,
            block_budget=settings.memory_block_budget,
            extractor=create_extractor(settings.memory_extractor),
        )
    return _memory_store


def set_memory_store(store: MemoryStore | None) -> None:
    """替换/重置记忆门面（测试与运行时切换用）。"""
    global _memory_store
    _memory_store = store


def get_llm_provider() -> LLMProvider:
    """懒加载 LLM provider（默认 mock：无 key 可跑通对话链路）。"""
    global _llm_provider
    if _llm_provider is None:
        settings = get_settings()
        _llm_provider = create_llm_provider(
            settings.llm_provider,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    return _llm_provider


def set_llm_provider(provider: LLMProvider | None) -> None:
    """替换/重置 LLM provider（测试与运行时切换用）。"""
    global _llm_provider
    _llm_provider = provider


class ChatRequest(BaseModel):
    """一次对话请求。"""

    text: str = Field(min_length=1, description="用户本次输入")
    session_id: str | None = Field(default=None, description="续聊时传入既有会话 id")
    persona_id: str = Field(default=_DEFAULT_PERSONA_ID, description="人设预设 id")
    user_name: str = Field(default="朋友", description="用户称呼")
    current_mood: str | None = Field(default=None, description="当前情绪标签（可选）")


class ChatResponse(BaseModel):
    """一轮对话的完整结果。"""

    session_id: str
    persona_id: str
    reply: str = Field(description="assistant 回复（mock provider 为占位文本）")
    system_prompt: str
    messages: list[dict[str, str]]
    worldbook_hits: list[str] = Field(description="命中的世界书条目 id")
    skipped: list[str] = Field(description="因预算被跳过的条目 id")
    memory_counts: dict[str, int] = Field(
        default_factory=dict, description="本轮召回的记忆数：memories/facts/summary"
    )
    remembered: dict[str, int] = Field(
        default_factory=dict, description="本轮写入的记忆数：facts/memory/summary"
    )
    warnings: list[str]
    estimated_tokens: int
    note: str = Field(description="模型提供商与运行模式说明")


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """一轮完整对话：召回 → 组装 → 生成 → 事件驱动写入。"""
    if req.persona_id not in _presets:
        raise HTTPException(status_code=404, detail=f"未知人设：{req.persona_id}")
    persona = _presets[req.persona_id]
    settings = get_settings()
    memory = get_memory_store()

    # 会话：续聊复用；新聊创建
    session = _repository.get(req.session_id) if req.session_id else None
    if session is None:
        state_vars = {"current_mood": req.current_mood} if req.current_mood else {}
        session = _repository.create(
            persona_id=req.persona_id,
            user_name=req.user_name,
            state_vars=state_vars,
            session_id=req.session_id,  # 客户端自定义 id 亦可，缺省自动生成
        )
    elif req.current_mood:
        session.set_state_var("current_mood", req.current_mood)

    # ① 组装提示（history 为本次输入前的既有轮次；含三层记忆召回）
    companion_id = req.persona_id  # 记忆按陪伴对象（角色）隔离
    assembled = assemble_chat(
        persona=persona,
        user_input=req.text,
        session=session,
        worldbook_entries=_entries,
        memory=memory,
        companion_id=companion_id,
    )

    # ② LLM 生成回复（默认 mock）
    provider = get_llm_provider()
    reply = provider.chat(
        [ChatMessage(**m) for m in assembled.to_messages()]
    )

    # ③ 回复后事件驱动写入（参照③④）
    turn_index = len(session.history) + 1
    remembered = memory.remember_turn(
        companion_id,
        req.text,
        reply,
        turn_index=turn_index,
        source=session.session_id,
        subject=req.user_name,
    )

    # ④ 会话历史追加 user / assistant
    _repository.append_turn(session.session_id, ChatTurn(role="user", text=req.text))
    _repository.append_turn(session.session_id, ChatTurn(role="assistant", text=reply))

    return ChatResponse(
        session_id=session.session_id,
        persona_id=req.persona_id,
        reply=reply,
        system_prompt=assembled.system_prompt,
        messages=assembled.to_messages(),
        worldbook_hits=[e.id for e in assembled.worldbook_hits],
        skipped=[e.id for e in assembled.skipped],
        memory_counts=assembled.memory_counts,
        remembered=remembered,
        warnings=assembled.warnings,
        estimated_tokens=assembled.estimated_tokens,
        note=(
            f"模型提供商：{provider.name}；记忆：召回+事件驱动写入已启用"
            f"（向量库 {settings.warm_backend}）"
        ),
    )
