"""SSML (Speech Synthesis Markup Language) tag helpers for TTS text.

Provides functions to wrap text with SSML tags commonly used in
professional TTS workflows: break, emphasis, prosody, and phoneme.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SSMLTag:
    """Represents an SSML tag that can be inserted into text."""

    label: str
    template: str
    description: str


# ── Standard SSML tags ────────────────────────────────────────────────────────

SSML_TAGS: list[SSMLTag] = [
    SSMLTag(
        label="停頓 (break)",
        template='<break time="{time}"/>',
        description="插入靜音停頓，例如 500ms",
    ),
    SSMLTag(
        label="強調 (emphasis)",
        template='<emphasis level="{level}">{text}</emphasis>',
        description="強調文字，level: strong / moderate / reduced",
    ),
    SSMLTag(
        label="語速語調 (prosody)",
        template='<prosody rate="{rate}" pitch="{pitch}">{text}</prosody>',
        description="調整語速和音調",
    ),
    SSMLTag(
        label="注音 (phoneme)",
        template='<phoneme alphabet="ipa" ph="{ph}">{text}</phoneme>',
        description="指定 IPA 發音",
    ),
    SSMLTag(
        label="段落 (p)",
        template="<p>{text}</p>",
        description="段落標記",
    ),
    SSMLTag(
        label="句子 (s)",
        template="<s>{text}</s>",
        description="句子標記",
    ),
]


def wrap_break(time_ms: int = 500) -> str:
    """Return a <break> tag with the given duration in milliseconds."""
    return f'<break time="{time_ms}ms"/>'


def wrap_emphasis(text: str, level: str = "moderate") -> str:
    """Wrap *text* in an <emphasis> tag."""
    if level not in ("strong", "moderate", "reduced"):
        level = "moderate"
    return f'<emphasis level="{level}">{text}</emphasis>'


def wrap_prosody(
    text: str,
    rate: str = "medium",
    pitch: str = "medium",
) -> str:
    """Wrap *text* in a <prosody> tag for rate/pitch control."""
    return f'<prosody rate="{rate}" pitch="{pitch}">{text}</prosody>'


def wrap_phoneme(text: str, ipa: str) -> str:
    """Wrap *text* with an IPA phoneme annotation."""
    return f'<phoneme alphabet="ipa" ph="{ipa}">{text}</phoneme>'


def wrap_ssml_document(body: str) -> str:
    """Wrap the full body in a complete SSML <speak> document."""
    return f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">\n{body}\n</speak>'


def strip_ssml(text: str) -> str:
    """Remove all XML/SSML tags, returning plain text."""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()
