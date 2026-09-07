"""时间衰减重排（纯函数，设计参照⑥）。

旧记忆让位于近期主线：召回时对相似度施加随记忆年龄递减的权重。
采用指数半衰期模型 —— half_life_days 天后权重恰好减半，直观可调。
"""

import math


def time_decay_weight(age_days: float, half_life_days: float = 30.0) -> float:
    """年龄 → 衰减权重（0, 1]。30 天半衰期意味着 30 天前的记忆权重约 0.5。

    参数:
        age_days: 记忆年龄（天，>=0）；
        half_life_days: 半衰期天数，越大衰减越慢。
    """
    if age_days <= 0:
        return 1.0
    if half_life_days <= 0:
        raise ValueError("half_life_days 必须为正数")
    return 0.5 ** (age_days / half_life_days)


def combined_score(
    similarity: float,
    age_days: float,
    *,
    half_life_days: float = 30.0,
    decay_exponent: float = 1.0,
) -> float:
    """组合分 = 相似度 × (时间衰减权重) ** decay_exponent。

    decay_exponent 控制衰减强度：
    - 0.0：完全不衰减（等价纯相似度排序）；
    - 1.0：标准半衰期衰减；
    - >1.0：更强地让位于近期记忆。
    """
    weight = time_decay_weight(age_days, half_life_days)
    if decay_exponent == 1.0:
        return similarity * weight
    return similarity * math.pow(weight, decay_exponent)
