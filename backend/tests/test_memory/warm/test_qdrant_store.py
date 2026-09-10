"""QdrantWarmStore 测试（本地 :memory: 模式，无需 Docker 与网络）。

注意：Qdrant 1.19+ 的检索 API 为 query_points（search 已移除）；
point id 必须为 UUID 格式（故 store 内部用 uuid4().hex）。
"""

from datetime import datetime, timedelta

import pytest

from app.memory.warm.qdrant_store import QdrantWarmStore


@pytest.fixture()
def store() -> QdrantWarmStore:
    """纯内存 Qdrant（每个测试独立实例）。"""
    return QdrantWarmStore(local_path=":memory:")


def test_add_and_count(store: QdrantWarmStore) -> None:
    store.add("therapist", "小林说他喜欢下雨天")
    store.add("therapist", "小林最近在换工作")
    assert store.count("therapist") == 2


def test_search_recalls_related(store: QdrantWarmStore) -> None:
    store.add("therapist", "小林说他喜欢下雨天，听着雨声很放松")
    store.add("therapist", "小林最近在换工作，压力很大")
    results = store.search("therapist", "工作压力", top_k=2)
    assert results
    assert "工作" in results[0].record.text
    assert results[0].raw_similarity >= results[1].raw_similarity


def test_companion_isolation(store: QdrantWarmStore) -> None:
    store.add("companion_a", "A 的独家记忆：怕黑")
    store.add("companion_b", "B 的独家记忆：恐高")
    results = store.search("companion_a", "独家记忆", top_k=5)
    assert len(results) == 1
    assert "怕黑" in results[0].record.text


def test_delete(store: QdrantWarmStore) -> None:
    mid = store.add("therapist", "可删的记忆")
    assert store.delete("therapist", mid) is True
    assert store.count("therapist") == 0
    # 重复删除同一 id：集合已空，仍返回 True（幂等）
    assert store.delete("therapist", mid) is True


def test_count_unknown_companion(store: QdrantWarmStore) -> None:
    assert store.count("never_used") == 0


def test_metadata_roundtrip(store: QdrantWarmStore) -> None:
    store.add("therapist", "小林养了只三花猫", metadata={"type": "preference", "mood": "轻松"})
    result = store.search("therapist", "猫", top_k=1)[0]
    assert result.record.metadata["type"] == "preference"
    assert result.record.metadata["mood"] == "轻松"


def test_time_decay_reranks_older_memory(store: QdrantWarmStore) -> None:
    """相同文本、不同时间：近期的应排前（应用层衰减重排生效）。"""
    now = datetime(2026, 9, 1)
    text = "小林怕打雷"
    store.add("therapist", text, memory_id="0" * 31 + "1", created_at=now - timedelta(days=120))
    store.add("therapist", text, memory_id="0" * 31 + "2", created_at=now - timedelta(days=1))

    results = store.search("therapist", text, top_k=2, now=now)
    assert len(results) == 2
    newer = max(r.record.created_at for r in results)
    assert results[0].record.created_at == newer  # 近期记忆排首位
    # 关闭衰减时两者分数接近（同文本同相似度）
    flat = store.search("therapist", text, top_k=2, now=now, decay_exponent=0.0)
    assert abs(flat[0].score - flat[1].score) < 1e-6


def test_top_k_limit(store: QdrantWarmStore) -> None:
    for i in range(8):
        store.add("therapist", f"小林今天做了第 {i} 件事")
    assert len(store.search("therapist", "小林今天做了事", top_k=3)) == 3


def test_requires_connection_params() -> None:
    with pytest.raises(ValueError):
        QdrantWarmStore()  # 既无 url 也无 local_path
