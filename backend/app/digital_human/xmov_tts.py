"""魔珐星云 TTS 客户端：文本 → 音频 + 字级时间戳。

两条通道：
- **WebSocket**（主）：`wss://{host}/user/v1/ws/tts?tts_vcn=...`
    发送 `{"text": "..."}`；接收：
      · data_type="CHAR_TIME_MAP" → 字级时间戳 JSON 字符串（口型对齐黄金数据）
      · data_type="AUDIO"        → base64 音频分片（拼接成完整音频）
      · inference_end=true       → 推理结束
- **REST**（兜底）：create_tts_task → get_tts_task 轮询取音频地址（无字级时间戳）

注意：官方示例中的 AK/Secret 为文档占位值，真实密钥请从控制台「密钥管理」获取，
并放 backend/.env（不入库）。
"""

import asyncio
import base64
import json
from dataclasses import dataclass, field

import httpx

from app.digital_human.xmov_auth import build_signature

# 默认端点与参数
XMOV_HOST = "nebula-agent.xingyun3d.com"
WS_PATH = "/user/v1/ws/tts"
REST_CREATE_PATH = "/user/v1/tts_task/create_tts_task"
REST_QUERY_PATH = "/user/v1/tts_task/get_tts_task"
DEFAULT_VOICE = "XMOV_LV_TTS__13"

# 标点占位（魔珐在字级时间戳中用 [PUNC] 表示标点）
PUNC_TOKEN = "[PUNC]"


class XmovTtsError(RuntimeError):
    """魔珐 TTS 调用失败。"""


@dataclass
class TtsResult:
    """一次语音合成的结果。"""

    audio_bytes: bytes = b""
    audio_format: str = "pcm"                    # 实测确认；默认按 PCM 处理
    char_times: list[tuple[str, float, float]] = field(default_factory=list)
    voice: str = ""
    duration_s: float = 0.0
    raw_messages: int = 0


async def synthesize_via_websocket(
    text: str,
    *,
    app_id: str,
    secret: str,
    voice: str = DEFAULT_VOICE,
    host: str = XMOV_HOST,
    timeout: float = 60.0,
) -> TtsResult:
    """WebSocket 通道：一次连接取回音频与字级时间戳。"""
    import websockets  # 延迟导入：仅 WebSocket 通道需要

    query = f"tts_vcn={voice}"
    api_path = f"{WS_PATH}?{query}"
    headers = build_signature(app_id, secret, "GET", api_path, {"tts_vcn": voice})
    url = f"wss://{host}{api_path}"

    audio_parts: list[bytes] = []
    char_times: list[tuple[str, float, float]] = []
    messages = 0
    end_time = 0.0

    async with websockets.connect(
        url, additional_headers=headers, open_timeout=timeout, close_timeout=5
    ) as ws:
        await ws.send(json.dumps({"text": text}, ensure_ascii=False))

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            except asyncio.TimeoutError as exc:  # 长时间无响应视为失败
                raise XmovTtsError(f"WebSocket 等待响应超时（已收到 {messages} 条消息）") from exc

            if isinstance(raw, bytes):       # 二进制帧：直接视作音频
                audio_parts.append(raw)
                continue

            message = json.loads(raw)
            messages += 1
            data_type = message.get("data_type")
            payload = message.get("data") or ""

            if data_type == "AUDIO" and payload:
                audio_parts.append(base64.b64decode(payload))
            elif data_type == "CHAR_TIME_MAP" and payload:
                char_times.extend(_parse_char_time_map(payload))

            end_time = max(end_time, float(message.get("end_time") or 0.0))

            if message.get("inference_end"):
                break

    return TtsResult(
        audio_bytes=b"".join(audio_parts),
        char_times=char_times,
        voice=voice,
        duration_s=end_time,
        raw_messages=messages,
    )


def _parse_char_time_map(payload: str) -> list[tuple[str, float, float]]:
    """解析字级时间戳：'[["这",0.0,0.134], ...]' → [(char, start_s, end_s)]。"""
    items = json.loads(payload)
    parsed: list[tuple[str, float, float]] = []
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        char = str(item[0])
        if char == PUNC_TOKEN:
            char = "，"          # 标点统一视作停顿（口型将映射为 SIL）
        parsed.append((char, float(item[1]), float(item[2])))
    return parsed


async def synthesize_via_rest(
    text: str,
    *,
    app_id: str,
    secret: str,
    voice: str = DEFAULT_VOICE,
    host: str = XMOV_HOST,
    timeout: float = 60.0,
    poll_interval: float = 1.0,
    max_polls: int = 60,
) -> TtsResult:
    """REST 通道（兜底）：创建任务 → 轮询结果 → 下载音频。

    该通道**不返回字级时间戳**（口型需按文本估算）。
    """
    base = f"https://{host}"
    create_data = {"text": text, "tts_vcn": voice}
    create_headers = build_signature(app_id, secret, "POST", REST_CREATE_PATH, create_data)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base}{REST_CREATE_PATH}", json=create_data, headers=create_headers
        )
        resp.raise_for_status()
        created = resp.json()
        if created.get("error_code") not in (0, None):
            raise XmovTtsError(f"创建任务失败：{created.get('error_reason')}")
        task_id = (created.get("data") or {}).get("task_id")
        if task_id is None:
            raise XmovTtsError(f"创建任务未返回 task_id：{created}")

        for _ in range(max_polls):
            query_path = f"{REST_QUERY_PATH}?task_id={task_id}"
            query_headers = build_signature(
                app_id, secret, "GET", query_path, {"task_id": task_id}
            )
            result = (await client.get(f"{base}{query_path}", headers=query_headers)).json()
            data = result.get("data") or {}
            audio_url = data.get("audio_url") or data.get("url")
            if audio_url:
                audio = (await client.get(audio_url)).content
                return TtsResult(audio_bytes=audio, voice=voice)
            await asyncio.sleep(poll_interval)

    raise XmovTtsError(f"轮询超时：task_id={task_id}")


def synthesize_sync(text: str, **kwargs) -> TtsResult:
    """同步封装（供同步调用方使用；不要在事件循环内调用）。"""
    return asyncio.run(synthesize_via_websocket(text, **kwargs))
