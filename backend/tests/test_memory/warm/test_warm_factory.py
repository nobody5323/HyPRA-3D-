"""温层工厂测试。"""

import pytest

from app.memory.warm.factory import create_warm_store
from app.memory.warm.inmemory_store import InMemoryWarmStore
from app.memory.warm.qdrant_store import QdrantWarmStore


def test_default_is_inmemory() -> None:
    store = create_warm_store()
    assert isinstance(store, InMemoryWarmStore)


def test_explicit_memory_backend() -> None:
    assert isinstance(create_warm_store("memory"), InMemoryWarmStore)


def test_qdrant_local_alias() -> None:
    """qdrant-local 别名：无 url 时走本地嵌入式内存模式（无需 Docker）。"""
    store = create_warm_store("qdrant-local")
    assert isinstance(store, QdrantWarmStore)
    # 可用性冒烟：写入 1 条
    store.add("t", "记忆")
    assert store.count("t") == 1


def test_qdrant_backend_with_local_path() -> None:
    store = create_warm_store("qdrant", local_path=":memory:")
    assert isinstance(store, QdrantWarmStore)


def test_unknown_backend_raises() -> None:
    with pytest.raises(ValueError):
        create_warm_store("redis")


def test_backend_case_insensitive() -> None:
    assert isinstance(create_warm_store("Memory"), InMemoryWarmStore)
