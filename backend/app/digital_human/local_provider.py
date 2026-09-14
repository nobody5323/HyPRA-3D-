"""本地降级实现：无音频、按文本估算的驱动数据（零依赖）。

用途：
- 评审环境不便配置魔珐账号时的兜底（前端仍能渲染"会说话"的数字人）；
- 单测与 CI（不依赖网络）。

产出：
- visemes：按文本估算的口型时间轴；
- face   ：整段表情（由 emotion/expression + intensity 驱动，含淡入淡出）；
- body   ：轻点头与手势（幅度随强度变化）。
"""

from app.digital_human.base import DigitalHumanProvider
from app.digital_human.models import AvatarOutput, BodyFrame, FaceFrame
from app.digital_human.viseme import (
    build_viseme_track_estimated,
    track_duration_ms,
)
from app.tools.emotion import EMOTION_FACIAL_EXPRESSIONS

# 默认音色/角色标识（本地实现无真实音频，仅作元数据）
DEFAULT_LOCAL_VOICE = "local-placeholder"


class LocalDigitalHumanProvider(DigitalHumanProvider):
    """本地占位实现（无音频，时间轴可用）。"""

    name = "local"

    def synthesize(
        self,
        text: str,
        *,
        emotion: str | None = None,
        expression: str | None = None,
        intensity: float = 0.5,
        voice: str | None = None,
    ) -> AvatarOutput:
        visemes = build_viseme_track_estimated(text)
        duration = track_duration_ms(visemes)
        resolved_expression = expression or EMOTION_FACIAL_EXPRESSIONS.get(
            emotion or "", "default"
        )
        face = _build_face_track(duration, resolved_expression, intensity)
        body = _build_body_track(duration, intensity)

        return AvatarOutput(
            text=text,
            provider=self.name,
            duration_ms=duration,
            visemes=visemes,
            face=face,
            body=body,
            audio_path=None,
            audio_base64=None,
            meta={
                "voice": voice or DEFAULT_LOCAL_VOICE,
                "emotion": emotion or "neutral",
                "expression": resolved_expression,
                "intensity": intensity,
                "note": "本地降级实现：无音频，前端可静音渲染或自行合成语音",
            },
        )


def _build_face_track(duration_ms: int, expression: str, intensity: float) -> list[FaceFrame]:
    """表情时间轴：淡入 → 保持 → 淡出（三段关键帧）。"""
    if duration_ms <= 0:
        return []
    peak = max(0.0, min(1.0, intensity))
    fade = min(300, duration_ms // 4)
    return [
        FaceFrame(start_ms=0, end_ms=fade, expression=expression, intensity=peak * 0.5),
        FaceFrame(
            start_ms=fade,
            end_ms=max(fade, duration_ms - fade),
            expression=expression,
            intensity=peak,
        ),
        FaceFrame(
            start_ms=max(fade, duration_ms - fade),
            end_ms=duration_ms,
            expression=expression,
            intensity=peak * 0.6,
        ),
    ]


def _build_body_track(duration_ms: int, intensity: float) -> list[BodyFrame]:
    """动作时间轴：静置 + 随强度变化的轻微点头。"""
    if duration_ms <= 0:
        return []
    amplitude = max(0.1, min(1.0, intensity))
    segment = max(1200, duration_ms // 3)
    frames: list[BodyFrame] = [
        BodyFrame(start_ms=0, end_ms=min(segment, duration_ms), gesture="lean_in", intensity=amplitude)
    ]
    cursor = segment
    index = 0
    while cursor < duration_ms:
        end = min(cursor + segment, duration_ms)
        frames.append(
            BodyFrame(
                start_ms=cursor,
                end_ms=end,
                gesture="nod" if index % 2 == 0 else "idle",
                intensity=amplitude * (0.8 if index % 2 == 0 else 0.5),
            )
        )
        cursor = end
        index += 1
    return frames
