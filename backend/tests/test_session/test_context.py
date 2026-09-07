"""会话上下文测试。"""

from app.session.context import DEFAULT_MAX_HISTORY_TURNS, ChatTurn, SessionContext


def _session(max_turns: int = 10) -> SessionContext:
    return SessionContext(
        session_id="s1",
        persona_id="therapist-elder-sister",
        user_name="小林",
        max_history_turns=max_turns,
    )


def test_default_window_size() -> None:
    assert DEFAULT_MAX_HISTORY_TURNS == 20


def test_append_keeps_recent_within_window() -> None:
    session = _session(max_turns=2)
    for i in range(4):
        session.append_turn(ChatTurn(role="user", text=f"m{i}"))
    assert len(session.history) == 2
    assert [t.text for t in session.history] == ["m2", "m3"]


def test_state_var_set() -> None:
    session = _session()
    session.set_state_var("current_mood", "焦虑")
    assert session.state_vars == {"current_mood": "焦虑"}
