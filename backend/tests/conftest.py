"""pytest 全局配置：测试隔离。

关键约束：**测试结果不得依赖本地 backend/.env 状态**，也不得发起真实网络请求。
- 记忆门面 → 临时 SQLite + 内存温层；
- LLM provider → 强制 mock（即使 .env 配了真实 key，常规测试也不联网）；
- 需要真实模型的联调测试见 tests/test_real_llm_smoke.py（默认 skip）。
"""

import pytest

from app.api import chat as chat_module
from app.llm.mock import MockLLMProvider
from app.memory.cold.sqlite_store import SqliteColdStore
from app.memory.store import MemoryStore
from app.memory.warm.inmemory_store import InMemoryWarmStore


@pytest.fixture(autouse=True)
def isolated_chat_dependencies(tmp_path):
    """自动替换 chat 模块的记忆门面与 LLM provider 为隔离实现。"""
    store = MemoryStore(
        SqliteColdStore(db_path=tmp_path / "memory.db"),
        InMemoryWarmStore(),
    )
    chat_module.set_memory_store(store)
    chat_module.set_llm_provider(MockLLMProvider())
    yield store
    chat_module.set_memory_store(None)
    chat_module.set_llm_provider(None)
