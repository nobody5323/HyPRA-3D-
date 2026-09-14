"""情绪日记存储测试。"""

import pytest

from app.memory.cold.mood_log import (
    MoodLogEntry,
    SqliteMoodLogStore,
)


@pytest.fixture()
def store(tmp_path) -> SqliteMoodLogStore:
    return SqliteMoodLogStore(db_path=tmp_path / "mood.db")


def _entry(**overrides) -> MoodLogEntry:
    base = {"companion_id": "therapist", "emotion": "anxious", "intensity": 0.7}
    base.update(overrides)
    return MoodLogEntry(**base)


def test_add_and_list(store: SqliteMoodLogStore) -> None:
    entry_id = store.add(_entry(trigger="工作汇报"))
    assert entry_id
    entries = store.list_recent("therapist")
    assert len(entries) == 1
    assert entries[0].emotion == "anxious"
    assert entries[0].trigger == "工作汇报"
    assert entries[0].intensity == 0.7


def test_list_isolated_by_companion(store: SqliteMoodLogStore) -> None:
    store.add(_entry(companion_id="companion_a", emotion="happy"))
    store.add(_entry(companion_id="companion_b", emotion="sad"))
    assert [e.emotion for e in store.list_recent("companion_a")] == ["happy"]
    assert [e.emotion for e in store.list_recent("companion_b")] == ["sad"]


def test_kebab_case_companion_id(store: SqliteMoodLogStore) -> None:
    """回归：带连字符的陪伴对象 id（真实 chat 用 persona.id）必须可用。"""
    store.add(_entry(companion_id="therapist-elder-sister"))
    assert len(store.list_recent("therapist-elder-sister")) == 1


def test_invalid_companion_id_rejected(store: SqliteMoodLogStore) -> None:
    with pytest.raises(ValueError):
        store.add(_entry(companion_id="坏 id;-"))
    with pytest.raises(ValueError):
        store.list_recent("坏 id;-")


def test_trend_empty(store: SqliteMoodLogStore) -> None:
    trend = store.trend("therapist", days=7)
    assert trend["total"] == 0
    assert trend["distribution"] == {}
    assert trend["avg_intensity"] == 0.0
    assert trend["dominant"] == ""


def test_trend_statistics(store: SqliteMoodLogStore) -> None:
    store.add(_entry(emotion="anxious", intensity=0.8))
    store.add(_entry(emotion="anxious", intensity=0.6))
    store.add(_entry(emotion="happy", intensity=0.4))

    trend = store.trend("therapist", days=7)
    assert trend["total"] == 3
    assert trend["distribution"] == {"anxious": 2, "happy": 1}
    assert trend["dominant"] == "anxious"
    assert trend["avg_intensity"] == pytest.approx(0.6, abs=0.01)


def test_trend_respects_day_window(store: SqliteMoodLogStore) -> None:
    """超出时间窗口的记录不计入趋势。"""
    from datetime import datetime, timedelta

    store.add(_entry(created_at=datetime.now() - timedelta(days=30), emotion="sad"))
    store.add(_entry(emotion="calm"))
    trend = store.trend("therapist", days=7)
    assert trend["total"] == 1
    assert trend["dominant"] == "calm"


def test_list_recent_orders_desc(store: SqliteMoodLogStore) -> None:
    from datetime import datetime, timedelta

    store.add(_entry(emotion="sad", created_at=datetime.now() - timedelta(hours=2)))
    store.add(_entry(emotion="happy"))
    entries = store.list_recent("therapist")
    assert entries[0].emotion == "happy"      # 最近的在前
