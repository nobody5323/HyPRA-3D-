"""chat 路由（骨架版）。

POST /chat：接收用户输入，返回组装好的完整提示（system / messages /
世界书命中信息）。当前不调用真实 LLM——assistant 生成将在接入模型后
于本路由内补齐；返回值中的 messages 已可直接喂给任何 OpenAI 兼容接口。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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

_DEFAULT_PERSONA_ID = "therapist-elder-sister"


class ChatRequest(BaseModel):
    """一次对话请求。"""

    text: str = Field(min_length=1, description="用户本次输入")
    session_id: str | None = Field(default=None, description="续聊时传入既有会话 id")
    persona_id: str = Field(default=_DEFAULT_PERSONA_ID, description="人设预设 id")
    user_name: str = Field(default="朋友", description="用户称呼")
    current_mood: str | None = Field(default=None, description="当前情绪标签（可选）")


class ChatResponse(BaseModel):
    """组装结果（LLM 调用前的完整上下文）。"""

    session_id: str
    persona_id: str
    system_prompt: str
    messages: list[dict[str, str]]
    worldbook_hits: list[str] = Field(description="命中的世界书条目 id")
    skipped: list[str] = Field(description="因预算被跳过的条目 id")
    warnings: list[str]
    estimated_tokens: int
    note: str = Field(description="当前为提示组装阶段，assistant 生成待接入 LLM")


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """组装一次对话提示并更新会话历史。"""
    if req.persona_id not in _presets:
        raise HTTPException(status_code=404, detail=f"未知人设：{req.persona_id}")
    persona = _presets[req.persona_id]

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

    # 组装提示（history 为本次输入前的既有轮次）
    assembled = assemble_chat(
        persona=persona,
        user_input=req.text,
        session=session,
        worldbook_entries=_entries,
    )

    # 把本次输入写入历史，供下一轮续聊
    _repository.append_turn(session.session_id, ChatTurn(role="user", text=req.text))

    return ChatResponse(
        session_id=session.session_id,
        persona_id=req.persona_id,
        system_prompt=assembled.system_prompt,
        messages=assembled.to_messages(),
        worldbook_hits=[e.id for e in assembled.worldbook_hits],
        skipped=[e.id for e in assembled.skipped],
        warnings=assembled.warnings,
        estimated_tokens=assembled.estimated_tokens,
        note="提示组装完成；assistant 回复生成待接入 LLM（后续里程碑）",
    )
