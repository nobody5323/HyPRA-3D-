"""模型适配档测试：匹配、合并、参数转换。"""

import pytest

from app.llm.profiles import (
    ModelProfile,
    load_model_profiles,
    resolve_profile,
    resolve_sampling,
)


@pytest.fixture()
def profiles() -> list[ModelProfile]:
    return load_model_profiles()


def test_profiles_loaded(profiles) -> None:
    ids = {p.id for p in profiles}
    assert "qwen3.7-flash" in ids
    assert "default" in ids


def test_match_qwen_model(profiles) -> None:
    profile = resolve_profile("qwen3.7-flash-2026-07-15", profiles)
    assert profile.id == "qwen3.7-flash"


def test_match_deepseek(profiles) -> None:
    profile = resolve_profile("deepseek-chat", profiles)
    assert profile.id == "deepseek"


def test_unknown_model_falls_back_to_default(profiles) -> None:
    profile = resolve_profile("some-unknown-model-xyz", profiles)
    assert profile.id == "default"


def test_longest_match_wins() -> None:
    """多个模式命中时取最长匹配（qwen3.7-flash 优先于 qwen）。"""
    items = [
        ModelProfile(id="generic-qwen", match=["qwen"], temperature=0.5),
        ModelProfile(id="specific", match=["qwen3.7-flash"], temperature=0.9),
    ]
    assert resolve_profile("qwen3.7-flash-x", items).id == "specific"


def test_empty_model_name_falls_back(profiles) -> None:
    assert resolve_profile("", profiles).id == "default"


# ---------- 采样参数合并 ----------


def test_style_sampling_overrides_profile(profiles) -> None:
    """文风预设的参数优先级更高（文风更贴近内容意图）。"""
    resolved = resolve_sampling(
        "qwen3.7-flash-2026-07-15",
        style_sampling={"temperature": 0.95, "max_tokens": 180},
        profiles=profiles,
    )
    assert resolved.temperature == 0.95          # 被文风覆盖
    assert resolved.max_tokens == 180            # 被文风覆盖
    assert resolved.top_p == 0.9                 # 模型档独有键保留
    assert resolved.sources["temperature"] == "style"
    assert resolved.sources["top_p"] == "qwen3.7-flash"


def test_profile_used_when_no_style_sampling(profiles) -> None:
    resolved = resolve_sampling("qwen3.7-flash-2026-07-15", None, profiles)
    assert resolved.frequency_penalty == 0.4
    assert resolved.profile_id == "qwen3.7-flash"
    assert resolved.style_hint  # 含该模型的格式约束


def test_to_provider_kwargs_skips_none() -> None:
    """None 参数不应进入请求（部分端点不接受 null）。"""
    resolved = resolve_sampling("unknown-model", None, [
        ModelProfile(id="minimal", match=["*"], temperature=0.7),
    ])
    kwargs = resolved.to_provider_kwargs()
    assert kwargs == {"temperature": 0.7}
    assert "top_p" not in kwargs
    assert "max_tokens" not in kwargs


def test_default_profile_has_hint(profiles) -> None:
    resolved = resolve_sampling("unknown", None, profiles)
    assert "列点" in resolved.style_hint or "客套" in resolved.style_hint
