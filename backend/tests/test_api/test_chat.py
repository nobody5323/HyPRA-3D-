"""POST /chat API 测试（TestClient，无真实 LLM）。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_returns_assembled_prompt() -> None:
    resp = client.post("/chat", json={"text": "我失眠了"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["system_prompt"].startswith("[角色人设]")
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][-1]["role"] == "user"
    # 触发世界书：失眠 → 深夜模式
    assert "night-mode" in body["worldbook_hits"]
    assert body["note"]


def test_chat_continuation_keeps_history() -> None:
    """同一 session_id 续聊：上一轮输入进入 messages 历史。"""
    first = client.post("/chat", json={"text": "昨天被老板批评了", "user_name": "小林"})
    sid = first.json()["session_id"]

    second = client.post("/chat", json={"text": "今天还是难受", "session_id": sid})
    assert second.status_code == 200
    roles = [m["role"] for m in second.json()["messages"]]
    contents = [m["content"] for m in second.json()["messages"]]
    # 历史含第一轮 user 输入
    assert "user" in roles[1:-1]
    assert "昨天被老板批评了" in contents
    assert contents[-1] == "今天还是难受"


def test_chat_unknown_persona_404() -> None:
    resp = client.post("/chat", json={"text": "hi", "persona_id": "no-such-persona"})
    assert resp.status_code == 404


def test_chat_empty_text_422() -> None:
    resp = client.post("/chat", json={"text": ""})
    assert resp.status_code == 422
