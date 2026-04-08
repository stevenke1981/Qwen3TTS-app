"""History management for TTS operations"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class HistoryEntry:
    id: str
    timestamp: str
    operation: str
    text: str
    ref_text: str | None = None
    ref_audio_name: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    audio_duration: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "text": self.text,
            "ref_text": self.ref_text,
            "ref_audio_name": self.ref_audio_name,
            "config": self.config,
            "audio_duration": self.audio_duration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        return cls(**data)


class HistoryManager:
    def __init__(self, storage_path: str | Path, max_entries: int = 100):
        self.storage_path = Path(storage_path)
        self.max_entries = max_entries
        self._entries: list[HistoryEntry] = []
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            with open(self.storage_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {"entries": []}
            self._entries = [HistoryEntry.from_dict(e) for e in data.get("entries", [])]

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"entries": [e.to_dict() for e in self._entries]}
        with open(self.storage_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

    def add(self, entry: HistoryEntry) -> None:
        self._entries.insert(0, entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[: self.max_entries]
        self._save()

    def get_all(self) -> list[HistoryEntry]:
        return self._entries.copy()

    def clear(self) -> None:
        self._entries.clear()
        self._save()

    def delete(self, entry_id: str) -> bool:
        """Delete a single entry by ID. Returns True if found and deleted."""
        original_len = len(self._entries)
        self._entries = [e for e in self._entries if e.id != entry_id]
        if len(self._entries) < original_len:
            self._save()
            return True
        return False

    def generate_id(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")
