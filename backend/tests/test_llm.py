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
    assert reply  # 空消息也不崩溃，返回通用承接话术


def test_mock_chat_empathizes_on_keywords() -> None:
    """命中关键词时给出对应共情话术（而非嵌入用户原文）。"""
    provider = MockLLMProvider()
    messages = [
        ChatMessage(role="system", content="你是苏澄。"),
        ChatMessage(role="user", content="我最近总是失眠，很困扰"),
    ]
    reply = provider.chat(messages)
    assert "睡" in reply or "休息" in reply
    assert "我最近总是失眠" not in reply  # 不再机械嵌入原文


def test_mock_chat_default_reply_for_plain_text() -> None:
    provider = MockLLMProvider()
    reply = provider.chat([ChatMessage(role="user", content="嗯嗯好的")])
    assert "我在这儿" in reply  # 通用承接话术
