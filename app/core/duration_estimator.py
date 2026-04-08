"""Estimate audio duration from text length and synthesis parameters.

Heuristic rules for professional TTS scheduling:
- Chinese:  ~3.5 characters/second at speed 1.0
- English:  ~2.5 words/second at speed 1.0
- Mixed:    weighted average

These are approximations; actual duration depends on the model and content.
"""

from __future__ import annotations

import re

# Characters per second at speed=1.0
_CJK_CPS = 3.5
_WORD_PS = 2.5   # English words per second

_CJK_RANGE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002b73f"
    r"\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]"
)


def _count_cjk(text: str) -> int:
    return len(_CJK_RANGE.findall(text))


def _count_words(text: str) -> int:
    """Count non-CJK words (split by whitespace)."""
    stripped = _CJK_RANGE.sub("", text)
    return len(stripped.split())


def estimate_duration(text: str, speed: float = 1.0) -> float:
    """Return estimated duration in seconds.

    Parameters
    ----------
    text:
        The synthesis source text.
    speed:
        TTS speed multiplier (1.0 = normal).

    Returns
    -------
    float
        Estimated duration in seconds (≥ 0.0).
    """
    if not text or not text.strip():
        return 0.0

    speed = max(speed, 0.1)  # prevent division by zero

    cjk_count = _count_cjk(text)
    word_count = _count_words(text)

    cjk_duration = cjk_count / _CJK_CPS
    word_duration = word_count / _WORD_PS

    total = (cjk_duration + word_duration) / speed
    return round(total, 1)


def format_duration(seconds: float) -> str:
    """Format seconds into a human-readable string like '1:23' or '0:05'."""
    if seconds <= 0:
        return "0:00"
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d}"
