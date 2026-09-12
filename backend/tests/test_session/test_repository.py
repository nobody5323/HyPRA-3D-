"""会话仓库（内存版）测试。"""

import pytest

from app.session.context import ChatTurn
from app.session.repository import SessionRepository


@pytest.fixture()
def repo() -> SessionRepository:
    return SessionRepository()


def test_create_and_get(repo: SessionRepository) -> None:
    session = repo.create("therapist-elder-sister", user_name="小林")
    got = repo.get(session.session_id)
    assert got is not None
    assert got.persona_id == "therapist-elder-sister"
    assert got.user_name == "小林"
    assert got.history == []


def test_duplicate_session_id_raises(repo: SessionRepository) -> None:
    repo.create("p1", session_id="fixed-id")
    with pytest.raises(ValueError):
        repo.create("p2", session_id="fixed-id")


def test_append_and_list_history(repo: SessionRepository) -> None:
    session = repo.create("p1")
    repo.append_turn(session.session_id, ChatTurn(role="user", text="你好"))
    repo.append_turn(session.session_id, ChatTurn(role="assistant", text="你好呀"))
    history = repo.list_history(session.session_id)
    assert [t.role for t in history] == ["user", "assistant"]
    assert [t.text for t in history] == ["你好", "你好呀"]


def test_history_window_trims_old_turns(repo: SessionRepository) -> None:
    """窗口上限内自动裁剪最旧消息，只保留最近 N 条。"""
    session = repo.create("p1", max_history_turns=3)
    for i in range(5):
        repo.append_turn(session.session_id, ChatTurn(role="user", text=f"msg{i}"))
    history = repo.list_history(session.session_id)
    assert len(history) == 3
    assert [t.text for t in history] == ["msg2", "msg3", "msg4"]


def test_get_missing_returns_none(repo: SessionRepository) -> None:
    assert repo.get("no-such-id") is None


def test_state_var_update(repo: SessionRepository) -> None:
    session = repo.create("p1")
    session.set_state_var("current_mood", "低落")
    assert session.state_vars["current_mood"] == "低落"
