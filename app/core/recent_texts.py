"""Recent synthesis texts — quick-reload queue for repeated TTS tasks."""

from __future__ import annotations

from pathlib import Path

import yaml

_RECENT_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "recent_texts.yaml"
_MAX_ITEMS = 20


def load_recent() -> list[str]:
    """Load recent texts from disk (newest first)."""
    if not _RECENT_FILE.exists():
        return []
    try:
        with open(_RECENT_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            return [str(item) for item in data[:_MAX_ITEMS]]
        return []
    except Exception:
        return []


def add_recent(text: str) -> list[str]:
    """Add *text* to the recent queue and persist.

    - Deduplicates (moves existing to front).
    - Caps at ``_MAX_ITEMS``.
    - Returns the updated list.
    """
    text = text.strip()
    if not text:
        return load_recent()

    items = load_recent()
    # Remove duplicate if it already exists
    items = [item for item in items if item != text]
    # Prepend
    items.insert(0, text)
    # Trim
    items = items[:_MAX_ITEMS]
    _save(items)
    return items


def clear_recent() -> None:
    """Remove all recent texts."""
    if _RECENT_FILE.exists():
        _RECENT_FILE.unlink()


def _save(items: list[str]) -> None:
    _RECENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_RECENT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(items, f, allow_unicode=True, default_flow_style=False)
