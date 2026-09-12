"""OpenAI 兼容 provider 测试（httpx.MockTransport 模拟，无网络、无 key）。"""

import json

import httpx
import pytest

from app.llm.base import ChatMessage
from app.llm.factory import create_llm_provider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import DEFAULT_BASE_URLS, OpenAICompatibleProvider


def _mock_client(handler) -> httpx.Client:
    """构造注入 MockTransport 的 httpx 客户端（供 openai SDK 使用）。"""
    return httpx.Client(transport=httpx.MockTransport(handler))


def _ok_handler(content: str = "我在听着呢。"):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1_700_000_000,
                "model": "qwen2.5-7b-instruct",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
            request=request,
        )

    return handler


def test_chat_returns_content() -> None:
    provider = OpenAICompatibleProvider(
        name="dashscope",
        api_key="test-key",
        model="qwen2.5-7b-instruct",
        http_client=_mock_client(_ok_handler("听起来你最近很不容易。")),
    )
    reply = provider.chat([ChatMessage(role="user", content="我最近很累")])
    assert reply == "听起来你最近很不容易。"


def test_request_payload_shape() -> None:
    """请求体应包含 model/messages/temperature，且 role 正确。"""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return _ok_handler()(request)

    provider = OpenAICompatibleProvider(
        name="dashscope",
        api_key="test-key",
        model="qwen2.5-7b-instruct",
        http_client=_mock_client(handler),
    )
    provider.chat(
        [
            ChatMessage(role="system", content="你是苏澄"),
            ChatMessage(role="user", content="你好"),
        ],
        temperature=0.3,
    )
    assert captured["model"] == "qwen2.5-7b-instruct"
    assert captured["temperature"] == 0.3
    assert [m["role"] for m in captured["messages"]] == ["system", "user"]


def test_authorization_header_uses_api_key() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return _ok_handler()(request)

    provider = OpenAICompatibleProvider(
        name="siliconflow",
        api_key="sk-abc123",
        model="Qwen/Qwen2.5-7B-Instruct",
        http_client=_mock_client(handler),
    )
    provider.chat([ChatMessage(role="user", content="hi")])
    assert seen["auth"] == "Bearer sk-abc123"


def test_default_base_urls() -> None:
    assert "dashscope" in DEFAULT_BASE_URLS
    assert "siliconflow" in DEFAULT_BASE_URLS
    assert DEFAULT_BASE_URLS["dashscope"].startswith("https://")


def test_explicit_base_url_overrides_default() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return _ok_handler()(request)

    provider = OpenAICompatibleProvider(
        name="openai-compatible",
        api_key="k",
        model="custom-model",
        base_url="https://my-endpoint.example.com/v1",
        http_client=_mock_client(handler),
    )
    provider.chat([ChatMessage(role="user", content="hi")])
    assert seen["url"].startswith("https://my-endpoint.example.com/v1")


def test_empty_choices_returns_empty_string() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": "x", "object": "chat.completion", "created": 1, "model": "m", "choices": []},
            request=request,
        )

    provider = OpenAICompatibleProvider(
        name="dashscope", api_key="k", model="m", http_client=_mock_client(handler)
    )
    assert provider.chat([ChatMessage(role="user", content="hi")]) == ""


def test_auth_error_raises() -> None:
    """401 应抛出 SDK 鉴权异常（不静默返回空串）。"""
    import openai

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"message": "Invalid API key", "type": "invalid_request_error"}},
            request=request,
        )

    provider = OpenAICompatibleProvider(
        name="dashscope",
        api_key="bad-key",
        model="m",
        max_retries=0,
        http_client=_mock_client(handler),
    )
    with pytest.raises(openai.AuthenticationError):
        provider.chat([ChatMessage(role="user", content="hi")])


def test_missing_api_key_raises() -> None:
    with pytest.raises(ValueError, match="api_key"):
        OpenAICompatibleProvider(name="dashscope", api_key="", model="m")


def test_missing_base_url_raises() -> None:
    """openai-compatible 无默认 base_url，必须显式提供。"""
    with pytest.raises(ValueError, match="base_url"):
        OpenAICompatibleProvider(name="openai-compatible", api_key="k", model="m")


# ---------- 工厂测试 ----------


def test_factory_mock_default() -> None:
    assert isinstance(create_llm_provider(""), MockLLMProvider)
    assert isinstance(create_llm_provider("mock"), MockLLMProvider)


def test_factory_dashscope() -> None:
    provider = create_llm_provider("dashscope", api_key="k", model="qwen2.5-7b-instruct")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "dashscope"


def test_factory_model_default_when_empty() -> None:
    provider = create_llm_provider("siliconflow", api_key="k")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.model  # 有兜底默认模型


def test_factory_unknown_raises() -> None:
    with pytest.raises(ValueError):
        create_llm_provider("not-a-provider")
