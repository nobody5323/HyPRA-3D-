"""LLM 工厂与 mock 实现测试。"""

import pytest

from app.llm.base import ChatMessage
from app.llm.factory import create_llm_provider
from app.llm.mock import MockLLMProvider


def test_factory_returns_mock_by_default() -> None:
    provider = create_llm_provider("")
    assert isinstance(provider, MockLLMProvider)
    assert provider.name == "mock"


def test_factory_mock_explicit() -> None:
    provider = create_llm_provider("mock")
    assert isinstance(provider, MockLLMProvider)


def test_factory_unknown_raises() -> None:
    with pytest.raises(ValueError):
        create_llm_provider("not-a-provider")


def test_factory_cloud_not_implemented() -> None:
    """真实云 provider 尚未接入：明确报 NotImplementedError 而非静默失败。"""
    with pytest.raises(NotImplementedError):
        create_llm_provider("dashscope", api_key="x")


def test_mock_chat_empty() -> None:
    provider = MockLLMProvider()
    reply = provider.chat([])
    assert "我" in reply  # 温柔基调占位回复


def test_mock_chat_anchors_on_last_user() -> None:
    provider = MockLLMProvider()
    messages = [
        ChatMessage(role="system", content="你是苏澄。"),
        ChatMessage(role="user", content="我最近总是失眠，很困扰"),
    ]
    reply = provider.chat(messages)
    # 占位回复应承接用户话题前 12 字
    assert "我最近总是失眠" in reply
