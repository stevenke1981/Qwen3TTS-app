"""Tests for app.core.history — HistoryManager and HistoryEntry."""

from __future__ import annotations

from pathlib import Path

from app.core.history import HistoryEntry, HistoryManager


class TestHistoryEntry:
    def test_to_dict_basic(self):
        entry = HistoryEntry(
            id="20250101_120000_000000",
            timestamp="2025-01-01 12:00:00",
            operation="tts",
            text="hello",
        )
        d = entry.to_dict()
        assert d["id"] == "20250101_120000_000000"
        assert d["operation"] == "tts"
        assert d["ref_text"] is None

    def test_from_dict_roundtrip(self):
        entry = HistoryEntry(
            id="test_id",
            timestamp="2025-01-01",
            operation="clone",
            text="test",
            ref_text="ref",
            config={"speed": 1.0},
            audio_duration=2.5,
        )
        restored = HistoryEntry.from_dict(entry.to_dict())
        assert restored.id == entry.id
        assert restored.ref_text == "ref"
        assert restored.audio_duration == 2.5
        assert restored.config == {"speed": 1.0}


class TestHistoryManager:
    def test_add_and_get_all(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml", max_entries=10)
        entry = HistoryEntry(
            id="001", timestamp="t1", operation="tts", text="hello"
        )
        mgr.add(entry)
        entries = mgr.get_all()
        assert len(entries) == 1
        assert entries[0].text == "hello"

    def test_newest_first(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml", max_entries=10)
        mgr.add(HistoryEntry(id="a", timestamp="1", operation="tts", text="first"))
        mgr.add(HistoryEntry(id="b", timestamp="2", operation="tts", text="second"))
        entries = mgr.get_all()
        assert entries[0].id == "b"
        assert entries[1].id == "a"

    def test_max_entries_enforced(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml", max_entries=3)
        for i in range(5):
            mgr.add(
                HistoryEntry(id=str(i), timestamp=str(i), operation="tts", text=f"t{i}")
            )
        assert len(mgr.get_all()) == 3
        # Newest entries should survive
        ids = [e.id for e in mgr.get_all()]
        assert "4" in ids
        assert "3" in ids
        assert "0" not in ids

    def test_clear(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml")
        mgr.add(HistoryEntry(id="x", timestamp="t", operation="tts", text="hi"))
        mgr.clear()
        assert mgr.get_all() == []

    def test_delete_returns_true_for_existing(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml")
        mgr.add(HistoryEntry(id="del_me", timestamp="t", operation="tts", text="bye"))
        assert mgr.delete("del_me") is True
        assert len(mgr.get_all()) == 0

    def test_delete_returns_false_for_missing(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml")
        assert mgr.delete("nonexistent") is False

    def test_persistence_across_instances(self, tmp_path: Path):
        path = tmp_path / "history.yaml"
        mgr1 = HistoryManager(path, max_entries=10)
        mgr1.add(HistoryEntry(id="p", timestamp="t", operation="tts", text="persist"))

        mgr2 = HistoryManager(path, max_entries=10)
        entries = mgr2.get_all()
        assert len(entries) == 1
        assert entries[0].id == "p"

    def test_generate_id_format(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml")
        id_ = mgr.generate_id()
        # Format: YYYYMMDD_HHMMSS_ffffff
        parts = id_.split("_")
        assert len(parts) == 3
        assert len(parts[0]) == 8  # date
        assert len(parts[1]) == 6  # time

    def test_get_all_returns_copy(self, tmp_path: Path):
        mgr = HistoryManager(tmp_path / "history.yaml")
        mgr.add(HistoryEntry(id="c", timestamp="t", operation="tts", text="copy"))
        entries = mgr.get_all()
        entries.clear()
        assert len(mgr.get_all()) == 1  # internal list unaffected
