"""模型适配档：per-model 的采样参数与技术性风格提示。

背景：不同模型对采样参数的容忍度、对格式指令的敏感度不同
（例：某些模型爱输出 markdown 列表与 emoji，需要额外提示压制）。
本档记录「技术适配」，与「文风预设」正交互补，两者合并后交给 provider。

合并规则（见 resolve_sampling）：
- 文风预设的 sampling 覆盖本档的 sampling（文风更贴近内容意图）；
- 本档独有的键（top_p / style_hint 等）保留。
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_PROFILES_FILE = Path(__file__).resolve().parent / "profiles.yaml"


class ModelProfile(BaseModel):
    """一个模型的适配档。"""

    id: str = Field(description="档位标识")
    match: list[str] = Field(default_factory=list, description="模型名匹配模式（子串）")
    temperature: float = Field(default=0.8, description="采样温度")
    top_p: float | None = Field(default=None, description="核采样阈值")
    frequency_penalty: float | None = Field(default=None, description="频率惩罚（抑制复读）")
    presence_penalty: float | None = Field(default=None, description="存在惩罚")
    max_tokens: int | None = Field(default=None, description="回复长度上限")
    style_hint: str = Field(default="", description="该模型特有的表达约束（附加到风格块）")

    @property
    def sampling(self) -> dict[str, float | int | None]:
        """本档的采样参数（未设置的项为 None，合并时跳过）。"""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "max_tokens": self.max_tokens,
        }


@dataclass
class ResolvedSampling:
    """模型档 ⊕ 文风预设 合并后的最终采样参数。"""

    temperature: float = 0.8
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    style_hint: str = ""
    profile_id: str = ""
    sources: dict[str, str] = field(default_factory=dict)

    def to_provider_kwargs(self) -> dict:
        """转成 provider.chat 的关键字参数（跳过 None，不污染请求）。"""
        kwargs: dict = {"temperature": self.temperature}
        for key in ("max_tokens", "top_p", "frequency_penalty", "presence_penalty"):
            value = getattr(self, key)
            if value is not None:
                kwargs[key] = value
        return kwargs


def load_model_profiles(file_path: str | Path = _PROFILES_FILE) -> list[ModelProfile]:
    """加载全部模型适配档（保序）。"""
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    items = raw.get("profiles") or []
    if not isinstance(items, list) or not items:
        raise ValueError(f"模型适配档 {path.name} 缺少 profiles 列表")
    return [ModelProfile.model_validate(item) for item in items]


def resolve_profile(
    model_name: str,
    profiles: list[ModelProfile] | None = None,
) -> ModelProfile:
    """按模型名解析适配档：取最长子串匹配；无匹配则用 default（或最后一个）。"""
    items = profiles if profiles is not None else load_model_profiles()

    best: ModelProfile | None = None
    best_len = -1
    for profile in items:
        for pattern in profile.match:
            if pattern == "*":
                continue
            if pattern and pattern.lower() in (model_name or "").lower():
                if len(pattern) > best_len:
                    best, best_len = profile, len(pattern)
    if best is not None:
        return best

    fallback = next((p for p in items if "*" in p.match), None)
    return fallback or items[-1]


def resolve_sampling(
    model_name: str,
    style_sampling: dict[str, float] | None = None,
    profiles: list[ModelProfile] | None = None,
) -> ResolvedSampling:
    """合并「模型适配档」与「文风预设建议参数」为最终采样参数。

    参数:
        model_name: 当前使用的模型名（用于匹配适配档）；
        style_sampling: 文风预设给出的建议参数（优先级更高）；
        profiles: 适配档列表（缺省从 profiles.yaml 读取）。
    """
    profile = resolve_profile(model_name, profiles)
    merged: dict = {}
    sources: dict[str, str] = {}

    # ① 模型档为基础
    for key, value in profile.sampling.items():
        if value is not None:
            merged[key] = value
            sources[key] = profile.id

    # ② 文风预设覆盖（文风更贴近内容意图）
    for key, value in (style_sampling or {}).items():
        if value is not None:
            merged[key] = value
            sources[key] = "style"

    return ResolvedSampling(
        temperature=float(merged.get("temperature", 0.8)),
        max_tokens=int(merged["max_tokens"]) if merged.get("max_tokens") else None,
        top_p=merged.get("top_p"),
        frequency_penalty=merged.get("frequency_penalty"),
        presence_penalty=merged.get("presence_penalty"),
        style_hint=profile.style_hint.strip(),
        profile_id=profile.id,
        sources=sources,
    )
