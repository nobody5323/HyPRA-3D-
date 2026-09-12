"""对话会话上下文：单轮消息与会话状态。

批次 D：为渲染管道提供统一的会话视图（历史窗口 + 状态变量）。
历史窗口先以进程内存实现，M2 升级独立 memory/hot 时替换来源。
"""

from dataclasses import dataclass, field


# 会话历史默认保留的消息条数（约 20 轮一往一返）
DEFAULT_MAX_HISTORY_TURNS = 20


@dataclass
class ChatTurn:
    """一条对话消息。"""

    role: str   # "user" | "assistant"
    text: str


@dataclass
class SessionContext:
    """一次陪伴会话的运行时状态。"""

    session_id: str
    persona_id: str
    user_name: str = "朋友"
    state_vars: dict[str, str] = field(default_factory=dict)
    history: list[ChatTurn] = field(default_factory=list)
    max_history_turns: int = DEFAULT_MAX_HISTORY_TURNS

    def append_turn(self, turn: ChatTurn) -> None:
        """追加一条消息，并自动裁剪超出窗口的旧消息（保留最近 N 条）。"""
        self.history.append(turn)
        if len(self.history) > self.max_history_turns:
            self.history = self.history[-self.max_history_turns:]

    def set_state_var(self, name: str, value: str) -> None:
        """更新一个动态状态变量（如 current_mood）。"""
        self.state_vars[name] = value
