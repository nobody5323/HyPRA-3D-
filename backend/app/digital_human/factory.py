"""数字人驱动工厂：按配置创建 provider。"""

from app.digital_human.base import DigitalHumanProvider
from app.digital_human.local_provider import LocalDigitalHumanProvider
from app.digital_human.xmov_provider import XmovDigitalHumanProvider


def create_digital_human_provider(
    provider: str = "local",
    *,
    app_id: str = "",
    secret: str = "",
    voice: str = "",
    host: str = "",
    media_dir: str = "media",
    fallback: DigitalHumanProvider | None = None,
) -> DigitalHumanProvider:
    """按名称创建数字人驱动 provider。

    参数:
        provider: local（零依赖降级，默认）| xmov（魔珐星云）；
        app_id / secret: 魔珐控制台密钥（xmov 时必填）；
        voice: 魔珐音色 ID（tts_vcn）；
        host: 魔珐服务主机；
        media_dir: 音频落盘目录；
        fallback: xmov 不可用时的降级实现（默认本地）。
    """
    name = (provider or "local").strip().lower()
    if name in {"local", "mock", "inmemory"}:
        return LocalDigitalHumanProvider()
    if name == "xmov":
        return XmovDigitalHumanProvider(
            app_id=app_id,
            secret=secret,
            voice=voice or "",
            host=host or "",
            media_dir=media_dir,
            fallback=fallback,
        )
    raise ValueError(f"未知数字人 provider：{provider!r}（可选 local | xmov）")
