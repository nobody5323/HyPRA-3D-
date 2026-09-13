"""LangGraph 节点实现（依赖注入式，便于单测与替换）。

节点职责（对应设计参照①的完整装配顺序）：
    load_persona → worldbook_recall → memory_recall
        → assemble_prompt → generate_reply → write_memory

各节点只做一件事，且都从 state 读取所需输入、返回增量字段；
外部依赖（人设/世界书/记忆/LLM/组装器）由构造参数注入。
"""

from app.llm.base import ChatMessage, LLMProvider
from app.llm.profiles import ResolvedSampling, resolve_sampling
from app.memory.store import MemoryStore
from app.prompts.assemble import assemble_worldbook_section
from app.prompts.persona.loader import PersonaPreset
from app.prompts.renderer import render_persona_prompt
from app.prompts.style.loader import check_persona_compatibility
from app.prompts.style.models import StylePreset
from app.rag.prompt_manager import PromptManager
from app.graph.state import ChatState
from app.tools.emotion import (
    EMOTION_TOOL_NAME,
    build_emotion_tool,
    extract_emotion_fallback,
    parse_emotion_result,
)
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
        styles: dict[str, StylePreset] | None = None,
        default_style_id: str = "modern-conversational",
        model_name: str = "",
    ) -> None:
        self.presets = presets
        self.entries = entries
        self.memory = memory_store
        self.llm = llm_provider
        self.prompt_manager = prompt_manager or PromptManager()
        self.worldbook_budget = worldbook_budget
        # 文风预设（与 persona 正交）：未注入时风格层为空（下游可选）
        self.styles = styles or {}
        self.default_style_id = default_style_id
        self.model_name = model_name or getattr(llm_provider, "model", "")

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
        """温层语义召回 + 冷层事实 + 摘要（按预判情绪加权，参照⑤）。

        时序说明：召回发生在生成之前，故用正则快速预判本轮情绪作为加权依据
        （生成后的精确情绪用于下一轮与记忆写入）。
        """
        pre_emotion = extract_emotion_fallback(state.get("user_input", ""))
        emotion_key = (
            pre_emotion.emotion.value
            if pre_emotion.emotion.value != "neutral"
            else None
        )
        ctx = self.memory.recall(
            state.get("companion_id", state["persona_id"]),
            state.get("user_input", ""),
            emotion=emotion_key,
        )
        return {
            "memory_context": ctx,
            "warm_lines": [r.record.text for r in ctx.memories],
            "fact_lines": [f.summary_text for f in ctx.facts],
            "summary_text": ctx.summary.content if ctx.summary else "",
            "warnings": self._merge_warnings(state, list(ctx.warnings)),
        }

    # ---------- ④ 分层组装 ----------

    def _resolve_style(self, state: ChatState) -> tuple[StylePreset | None, list[str]]:
        """解析本轮风格预设（state.style_id 优先，缺省用默认档），并做一致性校验。"""
        if not self.styles:
            return None, []
        style_id = state.get("style_id") or self.default_style_id
        style = self.styles.get(style_id)
        if style is None:
            return None, [f"未知风格预设「{style_id}」，已跳过风格层"]
        persona = self.presets.get(state["persona_id"])
        warnings = check_persona_compatibility(persona, style) if persona else []
        return style, warnings

    @staticmethod
    def _compose_style_text(style: StylePreset, style_hint: str) -> str:
        """风格指令块 = 文风预设指令 + 模型适配档的额外约束。"""
        parts = [style.instruction_block]
        if style_hint:
            parts.append(style_hint)
        return "\n\n".join(parts)

    def assemble_prompt(self, state: ChatState) -> dict:
        """用 PromptManager 按固定顺序与预算组装完整提示（含风格层与示例对话）。"""
        style, style_warnings = self._resolve_style(state)
        sampling: ResolvedSampling | None = None
        style_text = ""
        examples: list[tuple[str, str]] = []

        if style is not None:
            sampling = resolve_sampling(
                self.model_name, style.sampling, profiles=None
            )
            style_text = self._compose_style_text(style, sampling.style_hint)
            examples = [(e.user, e.assistant) for e in style.examples]

        built = self.prompt_manager.build(
            persona_text=state.get("persona_text", ""),
            user_input=state.get("user_input", ""),
            worldbook_text=state.get("worldbook_text", ""),
            warm_lines=state.get("warm_lines", []),
            fact_lines=state.get("fact_lines", []),
            summary_text=state.get("summary_text", ""),
            history=state.get("history", []),
            style_text=style_text,
            examples=examples,
        )
        return {
            "system_prompt": built.system_prompt,
            "messages": built.messages,
            "sampling": sampling,
            "style_id": style.id if style else "",
            "example_count": built.example_count,
            "warnings": self._merge_warnings(state, [*style_warnings, *built.warnings]),
        }

    # ---------- ⑤ LLM 生成 ----------

    def generate_reply(self, state: ChatState) -> dict:
        """生成回复 + 情绪识别（双通道），并应用「模型档 ⊕ 文风」采样参数。

        ① 主通道：function calling 结构化输出（回复 + 情绪标签一并返回）；
        ② 降级：模型不支持工具调用 / 调用失败 → 普通 chat() + 正则兜底情绪。
        两通道都保证给出非空回复与一个情绪结果，绝不空转。
        """
        messages = [ChatMessage(**m) for m in state.get("messages", [])]
        sampling: ResolvedSampling | None = state.get("sampling")
        kwargs = sampling.to_provider_kwargs() if sampling is not None else {}

        # ① 主通道：结构化输出
        tool_calls = self.llm.chat_with_tools(
            messages, [build_emotion_tool()], **kwargs
        )
        for call in tool_calls or []:
            if call.name != EMOTION_TOOL_NAME:
                continue
            result = parse_emotion_result(call.arguments)
            if result is not None:
                return {"reply": result.reply, "emotion": result}

        # ② 降级通道：普通回复 + 兜底情绪（用真实回复替换占位文本）
        reply = self.llm.chat(messages, **kwargs)
        fallback = extract_emotion_fallback(state.get("user_input", ""))
        fallback.reply = reply
        return {"reply": reply, "emotion": fallback}

    # ---------- ⑥ 回复后事件驱动写入 ----------

    def write_memory(self, state: ChatState) -> dict:
        """抽取事实 → 向量入库 → 摘要增量并入（参照③④）。

        本轮情绪作为 emotion_tag 随事实与向量一同落库，供后续加权召回。
        """
        emotion = state.get("emotion")
        writes = self.memory.remember_turn(
            state.get("companion_id", state["persona_id"]),
            state.get("user_input", ""),
            state.get("reply", ""),
            turn_index=state.get("turn_index", 0),
            source=state.get("session_id", ""),
            subject=state.get("user_name", "用户"),
            emotion=emotion.emotion.value if emotion is not None else None,
        )
        return {"writes": writes}
