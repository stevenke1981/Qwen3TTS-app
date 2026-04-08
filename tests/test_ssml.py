"""Tests for app.core.ssml — SSML tag helpers."""

from __future__ import annotations

from app.core.ssml import (
    SSML_TAGS,
    strip_ssml,
    wrap_break,
    wrap_emphasis,
    wrap_phoneme,
    wrap_prosody,
    wrap_ssml_document,
)


class TestSSMLTags:
    def test_builtin_tags_count(self):
        assert len(SSML_TAGS) >= 5

    def test_tags_have_required_fields(self):
        for tag in SSML_TAGS:
            assert tag.label
            assert tag.template
            assert tag.description


class TestWrapBreak:
    def test_default_time(self):
        result = wrap_break()
        assert 'time="500ms"' in result

    def test_custom_time(self):
        result = wrap_break(1000)
        assert 'time="1000ms"' in result


class TestWrapEmphasis:
    def test_default(self):
        result = wrap_emphasis("hello")
        assert "<emphasis" in result
        assert "hello" in result

    def test_level(self):
        result = wrap_emphasis("hello", level="strong")
        assert 'level="strong"' in result


class TestWrapProsody:
    def test_rate_only(self):
        result = wrap_prosody("hello", rate="fast")
        assert 'rate="fast"' in result
        assert "hello" in result

    def test_all_params(self):
        result = wrap_prosody("hi", rate="slow", pitch="high")
        assert 'rate="slow"' in result
        assert 'pitch="high"' in result


class TestWrapPhoneme:
    def test_basic(self):
        result = wrap_phoneme("text", "tɛkst")
        assert 'ph="tɛkst"' in result


class TestSSMLDocument:
    def test_wraps_in_speak_tags(self):
        result = wrap_ssml_document("hello world")
        assert "<speak" in result
        assert result.strip().endswith("</speak>")
        assert "hello world" in result


class TestStripSSML:
    def test_removes_tags(self):
        assert strip_ssml("<speak>hello <break time='1s'/> world</speak>") == "hello  world"

    def test_plain_text_unchanged(self):
        assert strip_ssml("hello world") == "hello world"
