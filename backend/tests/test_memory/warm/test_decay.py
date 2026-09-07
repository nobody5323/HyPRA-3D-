"""时间衰减纯函数测试。"""

import pytest

from app.memory.warm.decay import combined_score, time_decay_weight


def test_fresh_memory_full_weight() -> None:
    assert time_decay_weight(0) == 1.0
    assert time_decay_weight(-1) == 1.0  # 未来时间兜底


def test_half_life_halves_weight() -> None:
    """半衰期到达时权重应为 0.5。"""
    assert time_decay_weight(30, half_life_days=30) == pytest.approx(0.5)
    assert time_decay_weight(7, half_life_days=7) == pytest.approx(0.5)


def test_monotonic_decay() -> None:
    """年龄越大权重越低。"""
    weights = [time_decay_weight(d, half_life_days=30) for d in (0, 10, 30, 90, 365)]
    assert weights == sorted(weights, reverse=True)


def test_invalid_half_life_raises() -> None:
    with pytest.raises(ValueError):
        time_decay_weight(10, half_life_days=0)


def test_combined_score_no_decay_when_exponent_zero() -> None:
    """decay_exponent=0 时应等于纯相似度。"""
    assert combined_score(0.8, 365, decay_exponent=0.0) == pytest.approx(0.8)


def test_combined_score_standard_decay() -> None:
    """30 天年龄、0.5 相似度、30 天半衰期 → 0.25。"""
    assert combined_score(0.5, 30, half_life_days=30) == pytest.approx(0.25)


def test_combined_score_stronger_decay() -> None:
    """更大的 decay_exponent 使旧记忆分更低。"""
    weaker = combined_score(0.5, 30, half_life_days=30, decay_exponent=1.0)
    stronger = combined_score(0.5, 30, half_life_days=30, decay_exponent=3.0)
    assert stronger < weaker
