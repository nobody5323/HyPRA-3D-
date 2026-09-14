"""数字人驱动数据模型。

设计对齐魔珐星云「四路参数流」思路（audio / body / face / event），
但用后端可产出、前端可消费的**时间轴**表示：

    audio     语音（本模型中以音频文件/Base64 承载）
    visemes   口型时间轴（由文本 + 字级时间戳推导，驱动嘴型 blend shape）
    face      表情时间轴（由情绪链路 emotion / facial_expression 驱动）
    body      动作时间轴（由情绪强度驱动，如点头、手势幅度）

前端（魔珐 SDK 或 Three.js）读取这些时间轴即可渲染「会说话、有表情」的数字人。
"""

from dataclasses import dataclass, field
from enum import Enum


class Viseme(str, Enum):
    """口型单元（对齐常见 viseme 集合，便于映射到各家 blend shape）。"""

    SIL = "sil"   # 静默 / 闭口（标点、停顿）
    A = "A"       # 大张口（啊）
    I = "I"       # 扁口（衣）
    U = "U"       # 圆口（乌）
    E = "E"       # 中开（诶）
    O = "O"       # 圆唇（哦）
    M = "M"       # 闭唇（m / b / p）
    F = "F"       # 唇齿（f / v）
    N = "N"       # 舌尖（n / l / d / t）
    S = "S"       # 齿音（s / z / c / x）


@dataclass
class VisemeFrame:
    """一段口型帧（时间区间 + 口型）。"""

    start_ms: int
    end_ms: int
    viseme: Viseme
    char: str = ""       # 对应文字（调试与展示用）

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


@dataclass
class FaceFrame:
    """表情关键帧（时间区间 + 表情键 + 强度）。"""

    start_ms: int
    end_ms: int
    expression: str      # 与 EMOTION_FACIAL_EXPRESSIONS 的取值对齐
    intensity: float = 1.0


@dataclass
class BodyFrame:
    """动作关键帧（时间区间 + 动作键 + 幅度）。"""

    start_ms: int
    end_ms: int
    gesture: str = "idle"    # idle / nod / lean_in / hand_soft …
    intensity: float = 0.5


@dataclass
class AvatarOutput:
    """一次数字人驱动的完整产物。"""

    text: str
    provider: str
    duration_ms: int
    visemes: list[VisemeFrame] = field(default_factory=list)
    face: list[FaceFrame] = field(default_factory=list)
    body: list[BodyFrame] = field(default_factory=list)
    audio_path: str | None = None        # 本地音频文件路径（若有）
    audio_base64: str | None = None      # 音频 Base64（便于直接回传前端）
    audio_format: str = "mp3"
    meta: dict = field(default_factory=dict)

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_path or self.audio_base64)

    def to_dict(self) -> dict:
        """转成可直接 JSON 序列化的字典（供 API 响应）。"""
        return {
            "text": self.text,
            "provider": self.provider,
            "duration_ms": self.duration_ms,
            "has_audio": self.has_audio,
            "audio_format": self.audio_format,
            "audio_base64": self.audio_base64,
            "audio_path": self.audio_path,
            "visemes": [
                {"start_ms": f.start_ms, "end_ms": f.end_ms,
                 "viseme": f.viseme.value, "char": f.char}
                for f in self.visemes
            ],
            "face": [
                {"start_ms": f.start_ms, "end_ms": f.end_ms,
                 "expression": f.expression, "intensity": f.intensity}
                for f in self.face
            ],
            "body": [
                {"start_ms": f.start_ms, "end_ms": f.end_ms,
                 "gesture": f.gesture, "intensity": f.intensity}
                for f in self.body
            ],
            "meta": self.meta,
        }
