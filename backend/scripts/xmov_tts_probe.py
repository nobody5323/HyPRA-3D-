"""魔珐星云 TTS 联调探针（需 backend/.env 配置 XMOV_APP_ID / XMOV_SECRET）。

用途：在接入前端之前，先独立验证：
  1. 签名（X-TOKEN）是否正确 → 用 REST 创建任务验证；
  2. WebSocket 通道是否可用 → 取音频 + 字级时间戳；
  3. 音频格式与时长（决定前端播放与转码方式）。

用法（backend 目录下）：
    ../.venv/Scripts/python.exe scripts/xmov_tts_probe.py
    ../.venv/Scripts/python.exe scripts/xmov_tts_probe.py --text "自定义文本" --rest
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.digital_human.xmov_tts import (  # noqa: E402
    XmovTtsError,
    synthesize_via_rest,
    synthesize_via_websocket,
)

DEFAULT_TEXT = "你好，我是苏澄。今晚要是睡不着，我们就先聊一会儿。"


def guess_audio_format(data: bytes) -> str:
    """按文件头推测音频格式（便于确定前端播放方式）。"""
    if data[:3] == b"ID3":
        return "mp3 (ID3)"
    if data[:2] == b"\xff\xfb" or data[:2] == b"\xff\xf3":
        return "mp3 (frame sync)"
    if data[:4] == b"RIFF":
        return "wav"
    if data[:4] == b"OggS":
        return "ogg"
    return "未知（可能是裸 PCM）"


async def run(args) -> int:
    settings = get_settings()
    if not settings.xmov_app_id or not settings.xmov_secret:
        print("[!] 未配置 XMOV_APP_ID / XMOV_SECRET，请在 backend/.env 填写后重试。")
        return 1

    ak = settings.xmov_app_id
    print(f"AK: {ak[:8]}…（已配置） | 音色: {settings.xmov_voice} | host: {settings.xmov_host}")
    print(f"文本: {args.text}\n" + "=" * 60)

    # ---- ① REST 通道（同时验证签名是否正确）----
    if args.rest:
        print("\n=== REST 通道（验证签名）===")
        t0 = time.time()
        try:
            result = await synthesize_via_rest(
                args.text,
                app_id=ak,
                secret=settings.xmov_secret,
                voice=settings.xmov_voice,
                host=settings.xmov_host,
                timeout=60.0,
                max_polls=20,
            )
            print(f"  ✅ 签名有效，任务成功 | 耗时 {time.time()-t0:.1f}s | 音频 {len(result.audio_bytes)} 字节")
            print(f"  音频格式：{guess_audio_format(result.audio_bytes)}（REST 无字级时间戳）")
        except Exception as exc:
            print(f"  ❌ 失败：{type(exc).__name__}: {str(exc)[:200]}")

    # ---- ② WebSocket 通道（主通道：音频 + 字级时间戳）----
    print("\n=== WebSocket 通道（主通道）===")
    t0 = time.time()
    try:
        result = await synthesize_via_websocket(
            args.text,
            app_id=ak,
            secret=settings.xmov_secret,
            voice=settings.xmov_voice,
            host=settings.xmov_host,
            timeout=60.0,
        )
        elapsed = time.time() - t0
        print(f"  ✅ 成功 | 耗时 {elapsed:.1f}s")
        print(f"  音频：{len(result.audio_bytes)} 字节 | 格式推测：{guess_audio_format(result.audio_bytes)}")
        print(f"  字级时间戳：{len(result.char_times)} 条 | 语音时长：{result.duration_s:.2f}s | 消息数：{result.raw_messages}")
        if result.char_times:
            print(f"  样例：{result.char_times[:6]}")
        if result.audio_bytes:
            out_dir = Path(settings.media_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            sample = out_dir / "probe_ws_sample.bin"
            sample.write_bytes(result.audio_bytes)
            print(f"  样本已保存：{sample}")
    except XmovTtsError as exc:
        print(f"  ❌ TTS 错误：{exc}")
    except Exception as exc:
        print(f"  ❌ 失败：{type(exc).__name__}: {str(exc)[:200]}")

    print("\n" + "=" * 60)
    print("探针完成。若成功，请在 .env 设置 DIGITAL_HUMAN_PROVIDER=xmov 启用魔珐驱动。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="魔珐星云 TTS 联调探针")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="合成文本")
    parser.add_argument("--rest", action="store_true", help="附带测试 REST 通道（验证签名）")
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
