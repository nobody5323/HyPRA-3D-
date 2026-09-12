"""渲染总管道：把 persona / state_vars / worldbook / 记忆 / 会话历史组装成最终提示。

System Prompt 排版（对齐设计参照 8 条之 1）：

    [角色人设]      ← persona 文本（{{变量}} 已替换）
    [场景补充]      ← 世界书命中块（priority 序 + budget 约束）
    [记忆回忆]      ← 三层记忆召回（温层召回 > 冷层事实 > 摘要）

历史窗口置于 system 之后、本次输入之前，最终以 OpenAI 风格 messages 输出。
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.prompts.assemble import assemble_worldbook_section
from app.prompts.persona.loader import PersonaPreset
from app.prompts.renderer import estimate_tokens, render_persona_prompt
from app.session.context import ChatTurn, SessionContext
from app.worldbook.matcher import match_entries
from app.worldbook.models import WorldBookEntry

if TYPE_CHECKING:  # 仅类型标注，避免运行期循环导入
    from app.memory.store import MemoryStore

ROLE_DEF_SECTION = "角色人设"
WORLDBOOK_SECTION = "场景补充"

# 世界书注入块默认 token 预算
DEFAULT_WORLDBOOK_BUDGET = 400


@dataclass
class AssembledPrompt:
    """一次组装的结果。"""

    system_prompt: str
    history: list[ChatTurn]
    user_input: str
    worldbook_hits: list[WorldBookEntry] = field(default_factory=list)
    skipped: list[WorldBookEntry] = field(default_factory=list)
    memory_block: str = ""                      # 记忆召回块（无则为空）
    memory_counts: dict[str, int] = field(default_factory=dict)  # 各层召回数
    warnings: list[str] = field(default_factory=list)
    estimated_tokens: int = 0

    def to_messages(self) -> list[dict[str, str]]:
        """转成 OpenAI 风格 messages（system + 历史 + 本次 user 输入）。"""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        for turn in self.history:
            messages.append({"role": turn.role, "content": turn.text})
        messages.append({"role": "user", "content": self.user_input})
        return messages


def assemble_chat(
    persona: PersonaPreset,
    user_input: str,
    session: SessionContext,
    worldbook_entries: list[WorldBookEntry],
    *,
    worldbook_budget: int = DEFAULT_WORLDBOOK_BUDGET,
    scan_text: str | None = None,
    memory: "MemoryStore | None" = None,
    companion_id: str | None = None,
) -> AssembledPrompt:
    """组装一次对话的完整提示。

    参数:
        persona: 已加载的人设预设；
        user_input: 用户本次输入；
        session: 会话上下文（user_name / state_vars / history）；
        worldbook_entries: 参与匹配的世界书条目全集；
        worldbook_budget: 世界书注入块的 token 预算；
        scan_text: 世界书触发扫描的文本（默认即本次 user_input）；
        memory: 记忆门面（提供则召回三层记忆并插入记忆块）；
        companion_id: 陪伴对象 id（记忆隔离命名空间，缺省用 persona.id）。
    """
    # 1) 状态变量：user_name 兜底，session.state_vars 可覆盖
    context_vars = {"user_name": session.user_name, **session.state_vars}

    # 2) 渲染角色人设（含变量替换）
    persona_render = render_persona_prompt(persona, context_vars)
    persona_text = persona_render.text
    warnings = list(persona_render.warnings)

    # 3) 世界书：触发 → 注入编排
    scan = scan_text if scan_text is not None else user_input
    hits = match_entries(worldbook_entries, scan)
    worldbook_text, skipped = assemble_worldbook_section(hits, worldbook_budget)

    # 4) 记忆召回（温层语义 > 冷层事实 > 摘要）
    memory_block = ""
    memory_counts: dict[str, int] = {}
    if memory is not None:
        ctx = memory.recall(companion_id or persona.id, scan)
        memory_block = ctx.to_prompt_block(budget=memory.block_budget)
        warnings.extend(ctx.warnings)
        memory_counts = {
            "memories": len(ctx.memories),
            "facts": len(ctx.facts),
            "summary": 1 if (ctx.summary and ctx.summary.content.strip()) else 0,
        }

    # 5) 拼装 system prompt：人设 → 世界书 → 记忆（无内容则省略对应节）
    sections = [f"[{ROLE_DEF_SECTION}]\n{persona_text}"]
    if worldbook_text:
        sections.append(f"[{WORLDBOOK_SECTION}]\n{worldbook_text}")
    if memory_block:
        sections.append(memory_block)
    system_prompt = "\n\n".join(sections)

    return AssembledPrompt(
        system_prompt=system_prompt,
        history=list(session.history),
        user_input=user_input,
        worldbook_hits=hits,
        skipped=skipped,
        memory_block=memory_block,
        memory_counts=memory_counts,
        warnings=warnings,
        estimated_tokens=estimate_tokens(system_prompt),
    )
