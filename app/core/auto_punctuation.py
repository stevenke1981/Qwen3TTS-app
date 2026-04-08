"""Auto-punctuation post-processing for ASR transcripts.

Inserts basic Chinese sentence-ending punctuation based on simple
heuristics.  No external dependencies — works purely on text.

Usage::

    from app.core.auto_punctuation import add_punctuation
    result = add_punctuation("你好世界 接下來是什麼 今天天氣不錯吧")
    # → "你好世界，接下來是什麼？今天天氣不錯吧。"
"""

from __future__ import annotations

import re

# Characters that typically signal a question in Chinese
_QUESTION_WORDS = frozenset([
    "嗎", "嗎？", "什麼", "哪", "哪裡", "哪兒", "為什麼", "為何",
    "怎麼", "怎樣", "幾", "誰", "是不是", "有沒有", "可不可以", "能不能",
])

_SENTENCE_SPLITTER = re.compile(
    r"(?<=[^，。！？,!?…\s])\s+(?=[^\s])"
)


def _is_question(segment: str) -> bool:
    """Heuristic: does this segment look like a question?"""
    stripped = segment.rstrip()
    # Already punctuated
    if stripped and stripped[-1] in "？?！!。，,…":
        return False
    return any(word in stripped for word in _QUESTION_WORDS)


def add_punctuation(text: str, *, comma_join: bool = True) -> str:
    """Add basic Chinese punctuation to a raw ASR transcript.

    Parameters
    ----------
    text:
        Raw text from ASR (may contain spaces between spoken segments).
    comma_join:
        If True, multiple short segments within a sentence are joined with
        Chinese commas; if False, each segment is terminated individually.

    Returns
    -------
    str
        Text with punctuation inserted.
    """
    if not text or not text.strip():
        return text

    # If text already has dense punctuation, return as-is
    punc_chars = set("，。！？,!?.…")
    punc_ratio = sum(1 for c in text if c in punc_chars) / max(len(text), 1)
    if punc_ratio > 0.05:
        return text

    # Split on spaces (ASR often uses spaces as pseudo-boundaries)
    raw_segments = _SENTENCE_SPLITTER.split(text.strip())
    if not raw_segments:
        return text

    # Re-group into logical sentences of ≤40 characters
    sentences: list[list[str]] = [[]]
    current_len = 0
    for seg in raw_segments:
        if current_len + len(seg) > 40 and sentences[-1]:
            sentences.append([])
            current_len = 0
        sentences[-1].append(seg)
        current_len += len(seg)

    out_parts: list[str] = []
    for group in sentences:
        if not group:
            continue
        body = "，".join(group) if comma_join else " ".join(group)
        # Choose terminal punctuation
        if _is_question(body):
            body += "？"
        else:
            body += "。"
        out_parts.append(body)

    return "".join(out_parts)
