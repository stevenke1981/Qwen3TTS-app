"""Auto-save draft text across sessions."""

from __future__ import annotations

from pathlib import Path

import yaml

_DRAFTS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "drafts.yaml"


def save_drafts(drafts: dict[str, str]) -> None:
    """Save draft texts to disk. Keys: 'text_tab', 'clone_tab', 'clone_ref', 'edit_tab'."""
    _DRAFTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in drafts.items() if v and v.strip()}
    with open(_DRAFTS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(clean, f, allow_unicode=True, default_flow_style=False)


def load_drafts() -> dict[str, str]:
    """Load draft texts from disk."""
    if not _DRAFTS_FILE.exists():
        return {}
    try:
        with open(_DRAFTS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
