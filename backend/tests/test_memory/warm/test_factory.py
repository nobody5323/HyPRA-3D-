"""Embedding 工厂测试。"""

import pytest

from app.memory.warm.embedding import (
    DeterministicEmbeddingProvider,
    create_embedding_provider,
)


def test_create_default_deterministic() -> None:
    provider = create_embedding_provider("")
    assert isinstance(provider, DeterministicEmbeddingProvider)


def test_create_aliases() -> None:
    for name in ("deterministic", "memory", "mock"):
        provider = create_embedding_provider(name)
        assert isinstance(provider, DeterministicEmbeddingProvider)


def test_create_unknown_raises() -> None:
    with pytest.raises(ValueError):
        create_embedding_provider("weird-provider")


def test_create_cloud_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        create_embedding_provider("dashscope")
