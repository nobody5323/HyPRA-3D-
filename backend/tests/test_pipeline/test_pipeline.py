"""渲染总管道测试（端到端：人设 + 状态变量 + 世界书 + 历史）。"""

from app.prompts.persona.loader import load_builtin_presets
from app.prompts.pipeline import assemble_chat
from app.session.context import ChatTurn, SessionContext
from app.worldbook.loader import load_builtin_entries

PERSONA = load_builtin_presets()["therapist-elder-sister"]
ENTRIES = load_builtin_entries()


def _session(user_name: str = "小林", mood: str | None = "低落", history: list[ChatTurn] | None = None) -> SessionContext:
    state_vars = {"current_mood": mood} if mood else {}
    return SessionContext(
        session_id="s1",
        persona_id="therapist-elder-sister",
        user_name=user_name,
        state_vars=state_vars,
        history=history or [],
    )


def test_full_pipeline_triggers_worldbook() -> None:
    """输入含"失眠"→ 命中深夜模式；system 含设定文本，无残留宏。"""
    session = _session(mood="低落")
    result = assemble_chat(PERSONA, "我又失眠了，满脑子都是工作的事", session, ENTRIES)

    assert "night-mode" in [e.id for e in result.worldbook_hits]
    assert "深夜" in result.system_prompt or "失眠" in result.system_prompt
    assert "{{" not in result.system_prompt  # 所有状态变量都已替换
    assert result.skipped == []


def test_system_section_order_persona_first() -> None:
    """人设节应排在世界书节之前。"""
    session = _session()
    result = assemble_chat(PERSONA, "我今天在咨询室坐了一会儿", session, ENTRIES)

    assert "[角色人设]" in result.system_prompt
    assert "[场景补充]" in result.system_prompt
    assert result.system_prompt.index("[角色人设]") < result.system_prompt.index("[场景补充]")


def test_state_vars_injected_into_persona() -> None:
    session = _session(user_name="小林", mood="低落")
    result = assemble_chat(PERSONA, "我失眠了", session, ENTRIES)
    assert "小林" in result.system_prompt
    assert "低落" in result.system_prompt
    assert result.warnings == []


def test_missing_state_var_falls_back_with_warning() -> None:
    session = _session(mood=None)
    result = assemble_chat(PERSONA, "我失眠了", session, ENTRIES)
    assert "平静" in result.system_prompt  # current_mood 默认值
    assert len(result.warnings) >= 1


def test_messages_structure() -> None:
    """to_messages: system → 历史 → 本次 user 输入。"""
    history = [ChatTurn(role="user", text="昨天没睡好"), ChatTurn(role="assistant", text="听起来很辛苦")]
    session = _session(history=history)
    result = assemble_chat(PERSONA, "今天还是睡不着", session, ENTRIES)

    messages = result.to_messages()
    assert messages[0]["role"] == "system"
    assert [m["role"] for m in messages[1:-1]] == ["user", "assistant"]  # 历史
    assert messages[-1] == {"role": "user", "content": "今天还是睡不着"}
    assert result.estimated_tokens > 0


def test_tight_worldbook_budget_skips_low_priority() -> None:
    session = _session()
    # 预算极小 → 即便命中也应全部被跳过且不崩溃
    result = assemble_chat(PERSONA, "失眠了还想去咨询室看团子", session, ENTRIES, worldbook_budget=0)
    assert "[场景补充]" not in result.system_prompt
    assert result.worldbook_hits  # 确实命中了
    assert len(result.skipped) == len(result.worldbook_hits)


def test_no_worldbook_hit_omits_section() -> None:
    session = _session()
    result = assemble_chat(PERSONA, "今天天气不错", session, ENTRIES)
    assert result.worldbook_hits == []
    assert "[场景补充]" not in result.system_prompt
