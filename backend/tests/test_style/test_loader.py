"""风格预设加载与一致性校验测试。"""

import pytest

from app.prompts.persona.loader import load_builtin_presets
from app.prompts.style.loader import (
    check_persona_compatibility,
    load_builtin_styles,
    load_style_file,
)
from app.prompts.style.models import StyleExample, StylePreset

EXPECTED_IDS = {
    "modern-conversational",
    "classical-elegant",
    "brief-direct",
    "gentle-elaborate",
}


@pytest.fixture()
def styles() -> dict[str, StylePreset]:
    return load_builtin_styles()


def test_four_builtin_styles_loaded(styles) -> None:
    assert set(styles) == EXPECTED_IDS


def test_each_style_has_required_content(styles) -> None:
    """每个预设都应有正向指令 + 示例对话（反 AI 化的核心）。"""
    for style in styles.values():
        assert style.name
        assert style.description
        assert len(style.style_prompt.strip()) > 30, f"{style.id} 风格指令过短"
        assert style.example_count >= 2, f"{style.id} 示例对话不足 2 组"
        assert style.avoid, f"{style.id} 缺少必要禁令"


def test_examples_have_both_roles(styles) -> None:
    for style in styles.values():
        for example in style.examples:
            assert example.user.strip()
            assert example.assistant.strip()


def test_sampling_parameters_present(styles) -> None:
    """每个预设应给出建议采样参数（temperature 至少要有）。"""
    for style in styles.values():
        assert "temperature" in style.sampling, f"{style.id} 缺 temperature"
        assert 0.0 <= style.sampling["temperature"] <= 2.0
        assert style.sampling.get("max_tokens", 1) > 0


def test_instruction_block_contains_style_and_avoid(styles) -> None:
    block = styles["modern-conversational"].instruction_block
    assert "【表达风格：现代口语】" in block
    assert "避免：" in block


def test_brief_direct_limits_length(styles) -> None:
    """简短利落风格的 max_tokens 应明显小于细腻长句（文风差异体现在参数上）。"""
    brief = styles["brief-direct"].sampling["max_tokens"]
    elaborate = styles["gentle-elaborate"].sampling["max_tokens"]
    assert brief < elaborate


def test_consistency_check_no_conflict_for_therapist(styles) -> None:
    """苏澄（温柔倾听）与四个风格都不应冲突。"""
    persona = load_builtin_presets()["therapist-elder-sister"]
    for style in styles.values():
        assert check_persona_compatibility(persona, style) == [], style.id


def test_consistency_check_detects_conflict(styles) -> None:
    """人设含冲突特质时应给出告警。"""
    persona = load_builtin_presets()["therapist-elder-sister"]
    # 构造一个人设，其标签命中 classical-elegant 的 conflicts_with
    conflicting = persona.model_copy(update={"tags": [*persona.tags, "网络用语"]})
    warnings = check_persona_compatibility(conflicting, styles["classical-elegant"])
    assert warnings
    assert "网络用语" in warnings[0]


def test_loader_rejects_non_mapping(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- 只是列表\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_style_file(bad)


def test_loader_validates_required_fields(tmp_path) -> None:
    bad = tmp_path / "missing.yaml"
    bad.write_text("id: x\nname: X\n", encoding="utf-8")  # 缺 description/style_prompt
    with pytest.raises(Exception):
        load_style_file(bad)


def test_model_derived_fields() -> None:
    style = StylePreset(
        id="t", name="测试", description="d", style_prompt="多说人话。",
        avoid=["列点"], examples=[StyleExample(user="u", assistant="a")],
    )
    assert style.example_count == 1
    assert "【表达风格：测试】" in style.instruction_block
