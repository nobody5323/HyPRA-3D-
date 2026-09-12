"""pytest 全局配置：测试隔离。

所有测试使用「临时 SQLite + 内存温层」的记忆门面，避免污染 backend/data/。
"""

import pytest

from app.api import chat as chat_module
from app.memory.cold.sqlite_store import SqliteColdStore
from app.memory.store import MemoryStore
from app.memory.warm.inmemory_store import InMemoryWarmStore


@pytest.fixture(autouse=True)
def isolated_memory_store(tmp_path):
    """自动替换 chat 模块的记忆门面为隔离实例（测试结束重置）。"""
    store = MemoryStore(
        SqliteColdStore(db_path=tmp_path / "memory.db"),
        InMemoryWarmStore(),
    )
    chat_module.set_memory_store(store)
    yield store
    chat_module.set_memory_store(None)
