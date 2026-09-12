"""LangGraph 编排状态定义。

ChatState 是一轮对话在图中的流转载体：输入 → 中间产物 → 输出。
字段均可选（total=False），节点各自填充自己负责的部分。
"""

from typing import TypedDict

from app.memory.store import MemoryContext
from app.session.context import ChatTurn
from app.tools.emotion import EmotionResult
from app.worldbook.models import WorldBookEntry


class ChatState(TypedDict, total=False):
    """一轮对话的编排状态。"""

    # ---- 输入（chat 路由填充）----
    session_id: str
    companion_id: str            # 记忆隔离命名空间（= persona_id）
    persona_id: str
    user_name: str
    user_input: str
    history: list[ChatTurn]      # 本次输入之前的既有轮次
    turn_index: int              # 本轮序号（摘要并入用）
    state_vars: dict[str, str]   # 动态状态变量（current_mood 等）

    # ---- 中间产物（各节点填充）----
    persona_text: str
    worldbook_hits: list[WorldBookEntry]
    worldbook_skipped: list[WorldBookEntry]
    worldbook_text: str
    memory_context: MemoryContext | None
    warm_lines: list[str]        # 温层召回文本行
    fact_lines: list[str]        # 冷层事实文本行
    summary_text: str            # 冷层摘要
    system_prompt: str
    messages: list[dict[str, str]]

    # ---- 输出 ----
    reply: str
    emotion: EmotionResult | None   # 本轮情绪判定（结构化输出或兜底）
    writes: dict[str, int]       # 记忆写入统计
    warnings: list[str]
