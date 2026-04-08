"""Tests for app.core.recent_texts — recent texts queue."""

from __future__ import annotations

from pathlib import Path

from app.core.recent_texts import add_recent, clear_recent, load_recent


class TestRecentTexts:
    def test_load_empty(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.recent_texts._RECENT_FILE", tmp_path / "r.yaml")
        assert load_recent() == []

    def test_add_and_load(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.recent_texts._RECENT_FILE", tmp_path / "r.yaml")
        add_recent("hello")
        assert load_recent() == ["hello"]

    def test_dedup(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.recent_texts._RECENT_FILE", tmp_path / "r.yaml")
        add_recent("hello")
        add_recent("world")
        add_recent("hello")  # duplicate
        items = load_recent()
        assert items[0] == "hello"  # most recent first
        assert items.count("hello") == 1

    def test_max_items(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.recent_texts._RECENT_FILE", tmp_path / "r.yaml")
        monkeypatch.setattr("app.core.recent_texts._MAX_ITEMS", 3)
        for i in range(5):
            add_recent(f"item-{i}")
        assert len(load_recent()) == 3

    def test_clear(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.recent_texts._RECENT_FILE", tmp_path / "r.yaml")
        add_recent("hello")
        clear_recent()
        assert load_recent() == []

    def test_whitespace_stripped(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.recent_texts._RECENT_FILE", tmp_path / "r.yaml")
        add_recent("  hello  ")
        assert load_recent() == ["hello"]

    def test_empty_string_ignored(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.recent_texts._RECENT_FILE", tmp_path / "r.yaml")
        add_recent("")
        add_recent("   ")
        assert load_recent() == []
