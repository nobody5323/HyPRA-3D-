"""会话存储（进程内内存版）。

接口收敛为 create / get / append_turn / list_history，供 API 与测试使用。
M2 起如需持久化，可在此之上替换存储实现，调用方接口保持不变。
"""

import uuid

from app.session.context import ChatTurn, SessionContext


class SessionRepository:
    """内存会话注册表（单进程可用，重启即清空）。"""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}

    def create(
        self,
        persona_id: str,
        *,
        user_name: str = "朋友",
        state_vars: dict[str, str] | None = None,
        session_id: str | None = None,
        max_history_turns: int = 20,
    ) -> SessionContext:
        """创建新会话；session_id 缺省时自动生成。"""
        sid = session_id or uuid.uuid4().hex
        if sid in self._sessions:
            raise ValueError(f"会话已存在：{sid}")
        session = SessionContext(
            session_id=sid,
            persona_id=persona_id,
            user_name=user_name,
            state_vars=dict(state_vars or {}),
            max_history_turns=max_history_turns,
        )
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> SessionContext | None:
        """按 id 取会话，不存在返回 None。"""
        return self._sessions.get(session_id)

    def append_turn(self, session_id: str, turn: ChatTurn) -> SessionContext:
        """向会话追加一条消息（自动窗口裁剪），返回更新后的会话。"""
        session = self._require(session_id)
        session.append_turn(turn)
        return session

    def list_history(self, session_id: str) -> list[ChatTurn]:
        """返回会话历史副本（不会被外部修改）。"""
        return list(self._require(session_id).history)

    def _require(self, session_id: str) -> SessionContext:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"会话不存在：{session_id}")
        return session
