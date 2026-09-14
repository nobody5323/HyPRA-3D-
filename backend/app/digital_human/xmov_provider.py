"""魔珐星云数字人驱动实现（TTS WebSocket：音频 + 字级精确口型）。

流程：
    文本 + 情绪
      → 魔珐 TTS（WebSocket）：音频 + 字级时间戳 CHAR_TIME_MAP
      → 口型时间轴：字级时间戳 → viseme（精确对齐语音）
      → 表情/动作时间轴：emotion/expression + intensity 驱动
      → AvatarOutput（音频落盘 + 时间轴元数据）

失败策略：TTS 调用异常时**自动降级**到本地实现（不阻断前端渲染），
并在 meta 中标注降级原因，便于排查。
"""

from pathlib import Path

from app.digital_human.base import DigitalHumanProvider
from app.digital_human.local_provider import (
    LocalDigitalHumanProvider,
    _build_body_track,
    _build_face_track,
)
from app.digital_human.models import AvatarOutput
from app.digital_human.viseme import build_viseme_track_from_char_times
from app.digital_human.xmov_tts import (
    DEFAULT_VOICE,
    XMOV_HOST,
    XmovTtsError,
    synthesize_via_websocket,
    synthesize_sync,
)
from app.tools.emotion import EMOTION_FACIAL_EXPRESSIONS

# 音频分片默认格式（魔珐流式返回；如实测为 PCM，可由前端或后端转码）
DEFAULT_AUDIO_FORMAT = "pcm"


class XmovDigitalHumanProvider(DigitalHumanProvider):
    """魔珐星云实现（带本地降级）。"""

    name = "xmov"

    def __init__(
        self,
        *,
        app_id: str,
        secret: str,
        voice: str = DEFAULT_VOICE,
        host: str = XMOV_HOST,
        media_dir: str | Path = "media",
        audio_format: str = DEFAULT_AUDIO_FORMAT,
        timeout: float = 60.0,
        fallback: DigitalHumanProvider | None = None,
    ) -> None:
        if not app_id or not secret:
            raise ValueError("xmov provider 需要 XMOV_APP_ID 与 XMOV_SECRET（见 .env）")
        self.app_id = app_id
        self.secret = secret
        self.voice = voice or DEFAULT_VOICE
        self.host = host
        self.media_dir = Path(media_dir)
        self.audio_format = audio_format
        self.timeout = timeout
        self._fallback = fallback or LocalDigitalHumanProvider()

    def synthesize(
        self,
        text: str,
        *,
        emotion: str | None = None,
        expression: str | None = None,
        intensity: float = 0.5,
        voice: str | None = None,
    ) -> AvatarOutput:
        used_voice = voice or self.voice
        try:
            result = synthesize_sync(
                text,
                app_id=self.app_id,
                secret=self.secret,
                voice=used_voice,
                host=self.host,
                timeout=self.timeout,
            )
        except Exception as exc:  # 网络/鉴权/额度等异常 → 降级
            degraded = self._fallback.synthesize(
                text, emotion=emotion, expression=expression, intensity=intensity
            )
            degraded.meta.update(
                {"degraded_from": self.name, "degrade_reason": f"{type(exc).__name__}: {exc}"}
            )
            return degraded

        # ① 精确口型时间轴（字级时间戳）
        visemes = build_viseme_track_from_char_times(result.char_times)
        duration_ms = int(round(result.duration_s * 1000)) or (
            visemes[-1].end_ms if visemes else 0
        )

        # ② 表情与动作时间轴
        resolved_expression = expression or EMOTION_FACIAL_EXPRESSIONS.get(
            emotion or "", "default"
        )
        face = _build_face_track(duration_ms, resolved_expression, intensity)
        body = _build_body_track(duration_ms, intensity)

        # ③ 音频落盘（供前端按 URL 播放）
        audio_path = self._save_audio(text, result.audio_bytes) if result.audio_bytes else None

        return AvatarOutput(
            text=text,
            provider=self.name,
            duration_ms=duration_ms,
            visemes=visemes,
            face=face,
            body=body,
            audio_path=str(audio_path) if audio_path else None,
            audio_format=self.audio_format,
            meta={
                "voice": used_voice,
                "emotion": emotion or "neutral",
                "expression": resolved_expression,
                "intensity": intensity,
                "char_count": len(result.char_times),
                "audio_bytes": len(result.audio_bytes),
                "ws_messages": result.raw_messages,
            },
        )

    def _save_audio(self, text: str, audio: bytes) -> Path | None:
        """保存音频到 media 目录，返回路径。"""
        if not audio:
            return None
        import hashlib

        self.media_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.md5(f"{text}{len(audio)}".encode("utf-8")).hexdigest()[:12]
        path = self.media_dir / f"tts_{digest}.{self.audio_format}"
        path.write_bytes(audio)
        return path


__all__ = [
    "XmovDigitalHumanProvider",
    "XmovTtsError",
    "synthesize_via_websocket",
]
