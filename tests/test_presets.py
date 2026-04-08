"""Tests for app.core.presets — voice presets save/load."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.presets import (
    BUILTIN_PRESETS,
    VoicePreset,
    delete_custom_preset,
    load_presets,
    save_custom_preset,
)


class TestVoicePreset:
    def test_default_values(self):
        p = VoicePreset(name="test")
        assert p.speed == 1.0
        assert p.pitch == 1.0
        assert p.volume == 1.0

    def test_frozen_raises_on_assign(self):
        p = VoicePreset(name="test")
        with pytest.raises(AttributeError):
            p.name = "changed"  # type: ignore[misc]

    def test_to_dict(self):
        p = VoicePreset(name="快速", speed=1.5, pitch=1.0, volume=0.9)
        d = p.to_dict()
        assert d == {"name": "快速", "speed": 1.5, "pitch": 1.0, "volume": 0.9}

    def test_from_dict_full(self):
        d = {"name": "custom", "speed": 0.8, "pitch": 1.2, "volume": 0.7}
        p = VoicePreset.from_dict(d)
        assert p.name == "custom"
        assert p.speed == 0.8
        assert p.pitch == 1.2
        assert p.volume == 0.7

    def test_from_dict_partial_uses_defaults(self):
        d = {"name": "minimal"}
        p = VoicePreset.from_dict(d)
        assert p.speed == 1.0
        assert p.pitch == 1.0
        assert p.volume == 1.0

    def test_roundtrip_dict(self):
        original = VoicePreset(name="round", speed=0.5, pitch=1.5, volume=0.8)
        restored = VoicePreset.from_dict(original.to_dict())
        assert restored == original


class TestBuiltinPresets:
    def test_count(self):
        assert len(BUILTIN_PRESETS) == 5

    def test_names_are_unique(self):
        names = [p.name for p in BUILTIN_PRESETS]
        assert len(names) == len(set(names))

    def test_standard_is_first(self):
        assert BUILTIN_PRESETS[0].name == "標準"
        assert BUILTIN_PRESETS[0].speed == 1.0


class TestLoadSavePresets:
    def test_load_returns_builtins_when_no_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.presets._PRESETS_FILE", tmp_path / "none.yaml")
        presets = load_presets()
        assert len(presets) == len(BUILTIN_PRESETS)

    def test_save_and_load_custom(self, tmp_path: Path, monkeypatch):
        preset_file = tmp_path / "presets.yaml"
        monkeypatch.setattr("app.core.presets._PRESETS_FILE", preset_file)

        custom = VoicePreset(name="我的聲音", speed=1.2, pitch=0.9, volume=1.0)
        save_custom_preset(custom)

        presets = load_presets()
        custom_names = [p.name for p in presets if p.name == "我的聲音"]
        assert len(custom_names) == 1

    def test_save_multiple_custom(self, tmp_path: Path, monkeypatch):
        preset_file = tmp_path / "presets.yaml"
        monkeypatch.setattr("app.core.presets._PRESETS_FILE", preset_file)

        save_custom_preset(VoicePreset(name="A", speed=1.0))
        save_custom_preset(VoicePreset(name="B", speed=2.0))

        presets = load_presets()
        assert len(presets) == len(BUILTIN_PRESETS) + 2

    def test_delete_custom(self, tmp_path: Path, monkeypatch):
        preset_file = tmp_path / "presets.yaml"
        monkeypatch.setattr("app.core.presets._PRESETS_FILE", preset_file)

        save_custom_preset(VoicePreset(name="ToDelete", speed=1.0))
        delete_custom_preset("ToDelete")

        presets = load_presets()
        names = [p.name for p in presets]
        assert "ToDelete" not in names

    def test_delete_nonexistent_does_not_crash(self, tmp_path: Path, monkeypatch):
        preset_file = tmp_path / "presets.yaml"
        monkeypatch.setattr("app.core.presets._PRESETS_FILE", preset_file)
        # No file exists — should not raise
        delete_custom_preset("ghost")
