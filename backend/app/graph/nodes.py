"""LangGraph 节点实现（依赖注入式，便于单测与替换）。

节点职责（对应设计参照①的完整装配顺序）：
    load_persona → worldbook_recall → memory_recall
        → assemble_prompt → generate_reply → write_memory

各节点只做一件事，且都从 state 读取所需输入、返回增量字段；
外部依赖（人设/世界书/记忆/LLM/组装器）由构造参数注入。
"""

from app.llm.base import ChatMessage, LLMProvider
from app.memory.store import MemoryStore
from app.prompts.assemble import assemble_worldbook_section
from app.prompts.persona.loader import PersonaPreset
from app.prompts.renderer import render_persona_prompt
from app.rag.prompt_manager import PromptManager
from app.graph.state import ChatState
from app.worldbook.matcher import match_entries
from app.worldbook.models import WorldBookEntry


class ChatNodes:
    """一轮对话的全部节点（持有外部依赖）。"""

    def __init__(
        self,
        *,
        presets: dict[str, PersonaPreset],
        entries: list[WorldBookEntry],
        memory_store: MemoryStore,
        llm_provider: LLMProvider,
        prompt_manager: PromptManager | None = None,
        worldbook_budget: int = 400,
    ) -> None:
        self.presets = presets
        self.entries = entries
        self.memory = memory_store
        self.llm = llm_provider
        self.prompt_manager = prompt_manager or PromptManager()
        self.worldbook_budget = worldbook_budget

    # ---------- 工具 ----------

    @staticmethod
    def _merge_warnings(state: ChatState, new: list[str]) -> list[str]:
        return [*state.get("warnings", []), *new]

    # ---------- ① 人设渲染 ----------

    def load_persona(self, state: ChatState) -> dict:
        """渲染角色人设（状态变量替换）。"""
        persona = self.presets[state["persona_id"]]
        context_vars = {"user_name": state.get("user_name", "朋友"), **state.get("state_vars", {})}
        rendered = render_persona_prompt(persona, context_vars)
        return {
            "persona_text": rendered.text,
            "warnings": self._merge_warnings(state, list(rendered.warnings)),
        }

    # ---------- ② 世界书命中 ----------

    def worldbook_recall(self, state: ChatState) -> dict:
        """关键词/正则触发 + 注入编排（priority + 预算）。"""
        hits = match_entries(self.entries, state.get("user_input", ""))
        text, skipped = assemble_worldbook_section(hits, self.worldbook_budget)
        return {
            "worldbook_hits": hits,
            "worldbook_skipped": skipped,
            "worldbook_text": text,
        }

    # ---------- ③ 三层记忆召回 ----------

    def memory_recall(self, state: ChatState) -> dict:
        """温层语义召回 + 冷层事实 + 摘要。"""
        ctx = self.memory.recall(
            state.get("companion_id", state["persona_id"]),
            state.get("user_input", ""),
        )
        return {
            "memory_context": ctx,
            "warm_lines": [r.record.text for r in ctx.memories],
            "fact_lines": [f.summary_text for f in ctx.facts],
            "summary_text": ctx.summary.content if ctx.summary else "",
            "warnings": self._merge_warnings(state, list(ctx.warnings)),
        }

    # ---------- ④ 分层组装 ----------

    def assemble_prompt(self, state: ChatState) -> dict:
        """用 PromptManager 按固定顺序与预算组装完整提示。"""
        built = self.prompt_manager.build(
            persona_text=state.get("persona_text", ""),
            user_input=state.get("user_input", ""),
            worldbook_text=state.get("worldbook_text", ""),
            warm_lines=state.get("warm_lines", []),
            fact_lines=state.get("fact_lines", []),
            summary_text=state.get("summary_text", ""),
            history=state.get("history", []),
        )
        return {
            "system_prompt": built.system_prompt,
            "messages": built.messages,
            "warnings": self._merge_warnings(state, list(built.warnings)),
        }

    # ---------- ⑤ LLM 生成 ----------

    def generate_reply(self, state: ChatState) -> dict:
        """调用 LLM 生成助手回复。"""
        reply = self.llm.chat([ChatMessage(**m) for m in state.get("messages", [])])
        return {"reply": reply}

    # ---------- ⑥ 回复后事件驱动写入 ----------

    def write_memory(self, state: ChatState) -> dict:
        """抽取事实 → 向量入库 → 摘要增量并入（参照③④）。"""
        writes = self.memory.remember_turn(
            state.get("companion_id", state["persona_id"]),
            state.get("user_input", ""),
            state.get("reply", ""),
            turn_index=state.get("turn_index", 0),
            source=state.get("session_id", ""),
            subject=state.get("user_name", "用户"),
        )
        return {"writes": writes}
