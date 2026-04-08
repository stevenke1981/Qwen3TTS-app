"""Tests for app.core.drafts — auto-save draft text."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.core.drafts import load_drafts, save_drafts


class TestSaveDrafts:
    def test_save_creates_file(self, tmp_path: Path, monkeypatch):
        drafts_file = tmp_path / "data" / "drafts.yaml"
        monkeypatch.setattr("app.core.drafts._DRAFTS_FILE", drafts_file)

        save_drafts({"text_tab": "hello"})
        assert drafts_file.exists()

    def test_empty_values_are_stripped(self, tmp_path: Path, monkeypatch):
        drafts_file = tmp_path / "drafts.yaml"
        monkeypatch.setattr("app.core.drafts._DRAFTS_FILE", drafts_file)

        save_drafts({"text_tab": "hello", "clone_tab": "", "edit_tab": "   "})

        with open(drafts_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "text_tab" in data
        assert "clone_tab" not in data
        assert "edit_tab" not in data


class TestLoadDrafts:
    def test_missing_file_returns_empty(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.drafts._DRAFTS_FILE", tmp_path / "nope.yaml")
        assert load_drafts() == {}

    def test_roundtrip(self, tmp_path: Path, monkeypatch):
        drafts_file = tmp_path / "drafts.yaml"
        monkeypatch.setattr("app.core.drafts._DRAFTS_FILE", drafts_file)

        original = {"text_tab": "你好世界", "clone_tab": "reference text"}
        save_drafts(original)
        loaded = load_drafts()
        assert loaded == original

    def test_corrupt_file_returns_empty(self, tmp_path: Path, monkeypatch):
        drafts_file = tmp_path / "drafts.yaml"
        drafts_file.write_text("[invalid: {yaml: ]", encoding="utf-8")
        monkeypatch.setattr("app.core.drafts._DRAFTS_FILE", drafts_file)

        result = load_drafts()
        assert result == {}

    def test_non_dict_content_returns_empty(self, tmp_path: Path, monkeypatch):
        drafts_file = tmp_path / "drafts.yaml"
        drafts_file.write_text("- item1\n- item2\n", encoding="utf-8")
        monkeypatch.setattr("app.core.drafts._DRAFTS_FILE", drafts_file)

        result = load_drafts()
        assert result == {}
