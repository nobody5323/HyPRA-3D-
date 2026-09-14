"""Agent 工具循环测试：多轮调用、终止工具、降级、异常隔离。"""

import json

import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.graph.chat_graph import build_chat_graph
from app.graph.nodes import ChatNodes
from app.llm.base import ToolCall
from app.llm.mock import MockLLMProvider
from app.main import app
from app.memory.cold.mood_log import SqliteMoodLogStore
from app.memory.cold.sqlite_store import SqliteColdStore
from app.memory.store import MemoryStore
from app.memory.warm.inmemory_store import InMemoryWarmStore
from app.prompts.persona.loader import load_builtin_presets
from app.tools.builtin_tools import build_default_registry
from app.tools.emotion import EMOTION_TOOL_NAME
from app.worldbook.loader import load_builtin_entries

PERSONA_ID = "therapist-elder-sister"
client = TestClient(app)


def _emotion_call(reply: str = "我在听着呢", emotion: str = "anxious", **extra) -> ToolCall:
    payload = {"reply": reply, "emotion": emotion, "intensity": 0.7, **extra}
    return ToolCall(name=EMOTION_TOOL_NAME, arguments=json.dumps(payload, ensure_ascii=False))


@pytest.fixture()
def stores(tmp_path):
    mood = SqliteMoodLogStore(db_path=tmp_path / "mood.db")
    memory = MemoryStore(SqliteColdStore(db_path=tmp_path / "memory.db"), InMemoryWarmStore())
    return mood, memory


def _state(**overrides) -> dict:
    base = {
        "session_id": "s1",
        "companion_id": PERSONA_ID,
        "persona_id": PERSONA_ID,
        "user_name": "小林",
        "user_input": "我最近总是失眠，压力好大",
        "history": [],
        "turn_index": 1,
        "state_vars": {},
        "style_id": "",
        "warnings": [],
    }
    base.update(overrides)
    return base


def _graph(llm, stores, **node_overrides):
    mood, memory = stores
    nodes = ChatNodes(
        presets=load_builtin_presets(),
        entries=load_builtin_entries(),
        memory_store=memory,
        llm_provider=llm,
        tool_registry=build_default_registry(),
        mood_store=mood,
        **node_overrides,
    )
    return build_chat_graph(nodes)


# ---------- 多轮工具循环 ----------


def test_loop_executes_tool_then_returns_final(stores) -> None:
    """模型先调用工具，再调用终止工具 → 工具记录入 tools_used，回复来自终止工具。"""
    script = [
        [
            ToolCall(
                name="record_mood_journal",
                arguments=json.dumps({"emotion": "焦虑", "intensity": 0.8, "trigger": "失眠"}),
            )
        ],
        [_emotion_call("我听到了，先陪你缓一缓。")],
    ]
    llm = MockLLMProvider(scripted_rounds=script)
    result = _graph(llm, stores).invoke(_state())

    assert result["reply"] == "我听到了，先陪你缓一缓。"
    assert result["emotion"].emotion.value == "anxious"
    assert len(result["tools_used"]) == 1
    assert result["tools_used"][0]["name"] == "record_mood_journal"

    # 工具真的写入了日记
    mood, _ = stores
    entries = mood.list_recent(PERSONA_ID)
    assert len(entries) == 1
    assert entries[0].emotion == "anxious"
    assert entries[0].trigger == "失眠"


def test_loop_multiple_tools_in_one_round(stores) -> None:
    """同一轮调用多个工具，全部执行并记录。"""
    script = [
        [
            ToolCall(name="recall_memory", arguments=json.dumps({"query": "打雷"})),
            ToolCall(
                name="start_breathing_exercise",
                arguments=json.dumps({"pattern": "478", "cycles": 2}),
            ),
        ],
        [_emotion_call("我们慢慢来。")],
    ]
    result = _graph(MockLLMProvider(scripted_rounds=script), stores).invoke(_state())
    names = [t["name"] for t in result["tools_used"]]
    assert names == ["recall_memory", "start_breathing_exercise"]


def test_default_mock_has_no_tool_calls(stores) -> None:
    """默认 mock（无脚本）直接返回终止工具 → tools_used 为空但回复正常。"""
    result = _graph(MockLLMProvider(), stores).invoke(_state())
    assert result["reply"]
    assert result["tools_used"] == []


def test_tool_failure_does_not_break_conversation(stores) -> None:
    """工具执行失败（如缺依赖）仍能完成回复。"""
    script = [
        [ToolCall(name="no_such_tool", arguments="{}")],
        [_emotion_call("我们换个方式说说话。")],
    ]
    result = _graph(MockLLMProvider(scripted_rounds=script), stores).invoke(_state())
    assert result["reply"] == "我们换个方式说说话。"
    assert result["tools_used"][0]["name"] == "no_such_tool"
    assert "不存在" in result["tools_used"][0]["result"]      # 错误信息回传模型


def test_same_round_business_tool_not_lost(stores) -> None:
    """回归：模型在同一轮同时调用「业务工具」与「终止工具」时，

    业务工具必须照常执行（否则「帮我记一下」会静默失效）。
    真实模型（qwen）实测就存在这种同轮调用行为。
    """
    same_round = [
        ToolCall(
            name="record_mood_journal",
            arguments=json.dumps({"emotion": "焦虑", "intensity": 0.8, "trigger": "失眠"}),
        ),
        _emotion_call("抱抱，我一直在。"),
    ]
    result = _graph(MockLLMProvider(scripted_rounds=[same_round]), stores).invoke(_state())

    assert result["reply"] == "抱抱，我一直在。"          # 终止工具的回复生效
    assert len(result["tools_used"]) == 1                 # 业务工具也执行了
    assert result["tools_used"][0]["name"] == "record_mood_journal"

    mood, _ = stores
    assert len(mood.list_recent(PERSONA_ID)) == 1         # 日记确实落库


def test_loop_respects_max_rounds(stores) -> None:
    """轮数用尽后回落到纯文本回复（不会无限循环）。"""
    # 脚本一直返回工具调用，永不返回终止工具
    endless = [[ToolCall(name="recall_memory", arguments=json.dumps({"query": "x"}))]] * 5
    result = _graph(
        MockLLMProvider(scripted_rounds=endless), stores, max_tool_rounds=2
    ).invoke(_state())

    assert result["reply"]                       # 仍有回复（降级为文本）
    assert len(result["tools_used"]) == 2        # 最多执行 max_rounds 次


def test_graph_without_registry_still_works(tmp_path) -> None:
    """未注入工具注册表时（Agent 关闭）行为与 M4 一致。"""
    nodes = ChatNodes(
        presets=load_builtin_presets(),
        entries=load_builtin_entries(),
        memory_store=MemoryStore(SqliteColdStore(db_path=tmp_path / "m.db"), InMemoryWarmStore()),
        llm_provider=MockLLMProvider(),
    )
    result = build_chat_graph(nodes).invoke(_state())
    assert result["reply"]
    assert result["tools_used"] == []


# ---------- API 暴露 ----------


def test_chat_api_exposes_tools_used(stores) -> None:
    """chat 响应的 tools_used 应反映本轮实际调用的工具。"""
    script = [
        [ToolCall(name="query_mood_trend", arguments=json.dumps({"days": 7}))],
        [_emotion_call("我看了下你最近的状态。")],
    ]
    chat_module.set_llm_provider(MockLLMProvider(scripted_rounds=script))
    body = client.post("/chat", json={"text": "我最近状态怎么样"}).json()

    assert body["tools_used"]
    assert body["tools_used"][0]["name"] == "query_mood_trend"
    assert body["reply"] == "我看了下你最近的状态。"


def test_chat_api_tools_used_empty_by_default() -> None:
    body = client.post("/chat", json={"text": "你好"}).json()
    assert body["tools_used"] == []
