"""人设预设加载器测试。"""

from app.prompts.persona.loader import load_builtin_presets


def test_load_builtin_contains_therapist() -> None:
    """内置预设应包含 therapist-elder-sister。"""
    presets = load_builtin_presets()
    assert "therapist-elder-sister" in presets


def test_preset_schema_fields() -> None:
    """预设必填字段应完整且内容自洽。"""
    presets = load_builtin_presets()
    preset = presets["therapist-elder-sister"]

    assert preset.name == "苏澄"
    assert preset.creator == "hypra-original"  # 原创标记
    assert "温柔" in preset.tags
    assert "心理咨询" in preset.description
    # 声明用到的变量应全部已注册（避免渲染时出现"未知变量"告警）
    from app.prompts.state_vars.definitions import get_state_var

    assert all(get_state_var(v) is not None for v in preset.variables)


def test_preset_prompt_has_no_unregistered_var() -> None:
    """人设正文中的 {{变量}} 应都在注册表内。"""
    import re

    from app.prompts.persona.loader import load_builtin_presets
    from app.prompts.state_vars.definitions import get_state_var

    presets = load_builtin_presets()
    pattern = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")

    for preset in presets.values():
        for var_name in pattern.findall(preset.prompt):
            assert get_state_var(var_name) is not None, (
                f"预设 {preset.id} 引用了未注册变量 {var_name}"
            )
