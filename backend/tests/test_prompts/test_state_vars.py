"""状态变量宏替换器测试。"""

from app.prompts.state_vars.resolver import resolve_template


def test_replace_with_context() -> None:
    """命中 context 时应替换为用户提供的值，且无告警。"""
    text = "{{user_name}} 你好，今天心情是 {{current_mood}}。"
    resolved, warnings = resolve_template(text, {"user_name": "小林", "current_mood": "低落"})
    assert resolved == "小林 你好，今天心情是 低落。"
    assert warnings == []


def test_missing_var_falls_back_to_default() -> None:
    """context 缺失但注册表存在的变量 → 用默认值并给出告警。"""
    text = "{{current_mood}}"
    resolved, warnings = resolve_template(text, {})
    assert resolved == "平静"  # 注册表默认值
    assert len(warnings) == 1
    assert "默认值" in warnings[0]


def test_unknown_var_kept_with_warning() -> None:
    """完全未知的变量 → 保留原文并告警（不误伤普通文本）。"""
    text = "保留原文：{{not_a_var}}"
    resolved, warnings = resolve_template(text, {})
    assert resolved == "保留原文：{{not_a_var}}"
    assert len(warnings) == 1
    assert "未知" in warnings[0]


def test_no_vars_no_change() -> None:
    """不含宏的文本原样返回。"""
    text = "纯文本，没有变量。"
    resolved, warnings = resolve_template(text)
    assert resolved == text
    assert warnings == []
