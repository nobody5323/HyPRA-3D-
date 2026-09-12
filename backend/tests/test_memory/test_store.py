"""记忆门面（MemoryStore）测试：三层聚合、拼接顺序、预算、降级。"""

from datetime import datetime, timedelta

import pytest

from app.memory.cold.models import Fact, FactType
from app.memory.cold.sqlite_store import SqliteColdStore
from app.memory.store import MemoryContext, MemoryStore
from app.memory.warm.base import SearchResult, WarmMemoryStore
from app.memory.warm.inmemory_store import InMemoryWarmStore


@pytest.fixture()
def cold(tmp_path) -> SqliteColdStore:
    return SqliteColdStore(db_path=tmp_path / "memory.db")


@pytest.fixture()
def warm() -> InMemoryWarmStore:
    return InMemoryWarmStore()


@pytest.fixture()
def store(cold, warm) -> MemoryStore:
    return MemoryStore(cold, warm)


def _fact(**overrides) -> Fact:
    base = {
        "type": FactType.PREFERENCE,
        "subject": "小林",
        "predicate": "喜欢",
        "object": "下雨天",
    }
    base.update(overrides)
    return Fact(**base)


class _BrokenWarmStore(WarmMemoryStore):
    """模拟 Qdrant 不可用（连接失败）。"""

    def add(self, companion_id, text, **kw):  # pragma: no cover - 不使用
        raise RuntimeError("模拟连接失败")

    def search(self, companion_id, query, **kw):
        raise RuntimeError("模拟 Qdrant 连接失败")

    def delete(self, companion_id, memory_id):  # pragma: no cover
        return False

    def count(self, companion_id):  # pragma: no cover
        return 0


# ---------- 召回聚合 ----------


def test_recall_empty(store: MemoryStore) -> None:
    ctx = store.recall("therapist", "随便聊聊")
    assert ctx.empty is True
    assert ctx.to_prompt_block() == ""


def test_recall_aggregates_three_layers(cold, warm) -> None:
    warm.add("therapist", "小林说他喜欢下雨天，听着雨声很放松")
    cold.save_fact("therapist", _fact(object="猫"))
    cold.append_summary("therapist", scope_end=10, new_content="小林近期工作压力较大。")

    store = MemoryStore(cold, warm)
    ctx = store.recall("therapist", "下雨")

    assert len(ctx.memories) >= 1
    assert len(ctx.facts) == 1
    assert ctx.summary is not None
    assert ctx.empty is False


def test_facts_sorted_by_importance(cold, warm) -> None:
    cold.save_fact("therapist", _fact(object="小细节", importance=1))
    cold.save_fact("therapist", _fact(object="核心事实", importance=5))
    store = MemoryStore(cold, warm)

    ctx = store.recall("therapist", "小林")
    assert ctx.facts[0].object == "核心事实"  # 高 importance 优先


def test_companion_isolation_via_store(cold, warm) -> None:
    warm.add("companion_a", "A 的独家记忆：怕黑")
    cold.save_fact("companion_a", _fact(object="A 的猫"))
    store = MemoryStore(cold, warm)

    ctx_a = store.recall("companion_a", "独家记忆")
    ctx_b = store.recall("companion_b", "独家记忆")
    assert ctx_a.memories and ctx_a.facts
    assert ctx_b.empty is True


# ---------- 记忆块拼接 ----------


def test_prompt_block_order(cold, warm) -> None:
    """块内顺序：相关回忆 > 已知事实 > 会话摘要（对齐参照①）。"""
    warm.add("therapist", "小林喜欢下雨天")
    cold.save_fact("therapist", _fact(object="猫"))
    cold.append_summary("therapist", scope_end=10, new_content="小林近期压力大。")
    store = MemoryStore(cold, warm)

    block = store.recall("therapist", "下雨").to_prompt_block()
    assert block.startswith("[记忆回忆]")
    assert block.index("相关回忆") < block.index("已知事实") < block.index("会话摘要")


def test_prompt_block_budget_truncates(cold, warm) -> None:
    """预算不足时只装入高优先部分（回忆优先，事实被裁）。"""
    warm.add("therapist", "小林喜欢下雨天")
    cold.save_fact("therapist", _fact(object="很长的细节描述" * 20))
    store = MemoryStore(cold, warm)

    ctx = store.recall("therapist", "下雨")
    small = ctx.to_prompt_block(budget=25)
    assert "相关回忆" in small
    assert "已知事实" not in small  # 预算耗尽后不再追加低优先内容


def test_prompt_block_too_small_returns_empty(cold, warm) -> None:
    """预算连一条都装不下时返回空串（不注入只有标题的空块）。"""
    warm.add("therapist", "小林喜欢下雨天" * 20)
    store = MemoryStore(cold, warm)
    ctx = store.recall("therapist", "下雨")
    assert ctx.to_prompt_block(budget=5) == ""


def test_prompt_block_omits_empty_sections(cold, warm) -> None:
    warm.add("therapist", "小林喜欢下雨天")
    store = MemoryStore(cold, warm)
    block = store.recall("therapist", "下雨").to_prompt_block()
    assert "相关回忆" in block
    assert "已知事实" not in block
    assert "会话摘要" not in block


# ---------- 容错降级 ----------


def test_warm_failure_degrades_gracefully(cold) -> None:
    """温层不可用时：仍返回冷层内容，并记 warning（不抛异常）。"""
    cold.save_fact("therapist", _fact(object="猫"))
    store = MemoryStore(cold, _BrokenWarmStore())

    ctx = store.recall("therapist", "猫")
    assert ctx.facts  # 冷层仍可用
    assert ctx.memories == []
    assert any("温层召回失败" in w for w in ctx.warnings)


def test_memory_context_empty_flag() -> None:
    assert MemoryContext().empty is True
    assert MemoryContext(facts=[_fact()]).empty is False
