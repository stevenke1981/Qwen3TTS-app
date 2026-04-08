"""Voice preset profiles — save/load speed, pitch, volume combinations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

_PRESETS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "presets.yaml"


@dataclass(frozen=True)
class VoicePreset:
    name: str
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> VoicePreset:
        return cls(
            name=d["name"],
            speed=d.get("speed", 1.0),
            pitch=d.get("pitch", 1.0),
            volume=d.get("volume", 1.0),
        )


# Built-in presets
BUILTIN_PRESETS = [
    VoicePreset(name="標準", speed=1.0, pitch=1.0, volume=1.0),
    VoicePreset(name="高速朗讀", speed=1.5, pitch=1.0, volume=1.0),
    VoicePreset(name="低速柔和", speed=0.7, pitch=0.9, volume=0.8),
    VoicePreset(name="高亢", speed=1.0, pitch=1.3, volume=1.0),
    VoicePreset(name="低沉", speed=0.9, pitch=0.7, volume=1.0),
]


def load_presets() -> list[VoicePreset]:
    """Load presets from disk, merging with built-ins."""
    presets = list(BUILTIN_PRESETS)
    if _PRESETS_FILE.exists():
        try:
            with open(_PRESETS_FILE, encoding="utf-8") as f:
                data = yaml.safe_load(f) or []
            for item in data:
                presets.append(VoicePreset.from_dict(item))
        except Exception:
            pass
    return presets


def save_custom_preset(preset: VoicePreset) -> None:
    """Append a custom preset to disk."""
    _PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if _PRESETS_FILE.exists():
        try:
            with open(_PRESETS_FILE, encoding="utf-8") as f:
                existing = yaml.safe_load(f) or []
        except Exception:
            existing = []
    existing.append(preset.to_dict())
    with open(_PRESETS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(existing, f, allow_unicode=True, default_flow_style=False)


def delete_custom_preset(name: str) -> None:
    """Remove a custom preset by name."""
    if not _PRESETS_FILE.exists():
        return
    try:
        with open(_PRESETS_FILE, encoding="utf-8") as f:
            existing = yaml.safe_load(f) or []
        filtered = [p for p in existing if p.get("name") != name]
        with open(_PRESETS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(filtered, f, allow_unicode=True, default_flow_style=False)
    except Exception:
        pass
