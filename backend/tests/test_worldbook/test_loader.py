"""世界书条目加载测试。"""

from app.worldbook.loader import load_builtin_entries


def test_builtin_entries_loaded() -> None:
    """内置条目应加载齐全。"""
    entries = load_builtin_entries()
    ids = {e.id for e in entries}
    assert {"consulting-room", "night-mode", "pet-cat"} <= ids


def test_every_entry_has_trigger() -> None:
    """每条目都应有触发条件（关键词或正则至少一项）。"""
    for entry in load_builtin_entries():
        assert entry.has_trigger, f"条目 {entry.id} 缺少触发条件"


def test_entry_fields() -> None:
    """字段完整性抽查。"""
    entries = {e.id: e for e in load_builtin_entries()}
    room = entries["consulting-room"]
    assert "咨询室" in room.keys
    assert "梧桐" in room.content  # 自创细节存在
    assert room.priority == 10

    night = entries["night-mode"]
    assert night.keys == []
    assert night.regex  # 正则条目
