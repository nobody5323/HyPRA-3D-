"""魔珐星云鉴权：X-TOKEN 签名。

官方算法（见《语音合成API说明》1.1）：
    ori_sign = lower(api_path) + lower(method) + sort_json + secret + timestamp
    X-TOKEN  = md5(ori_sign)

其中 sort_json 为请求数据体按键排序、去空格后的 JSON 字符串。
请求头：X-APP-ID / X-TIMESTAMP / X-TOKEN。

纯标准库实现（hashlib + json + time），无额外依赖。
"""

import hashlib
import json
import time


def encode_with_md5(text: str) -> str:
    """MD5 十六进制摘要。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def build_signature(
    app_id: str,
    secret: str,
    method: str,
    api_path: str,
    data: dict | None = None,
    timestamp: int | None = None,
) -> dict[str, str]:
    """生成带签名的请求头。

    参数:
        app_id: 应用 AK（控制台「密钥管理」获取）；
        secret: 应用 Secret；
        method: HTTP 方法（GET/POST，大小写不敏感）；
        api_path: 接口路径（含 query，如 "/user/v1/ws/tts"）；
        data: 请求数据体（参与签名；WebSocket 试听传参数表）；
        timestamp: 秒级时间戳（默认当前时间，测试可注入）。
    """
    ts = int(timestamp if timestamp is not None else time.time())
    payload = json.dumps(dict(data or {}), sort_keys=True).replace(" ", "")
    origin = f"{api_path.lower()}{method.lower()}{payload}{secret}{ts}"
    return {
        "X-APP-ID": app_id,
        "X-TOKEN": encode_with_md5(origin),
        "X-TIMESTAMP": str(ts),
    }
