"""Tests for app.core.duration_estimator."""

from __future__ import annotations

from app.core.duration_estimator import estimate_duration, format_duration


class TestEstimateDuration:
    def test_empty_text(self):
        assert estimate_duration("") == 0.0

    def test_cjk_text(self):
        # 10 CJK characters at default speed (1.0) → ~10/3.5 ≈ 2.86s
        dur = estimate_duration("你好世界你好世界你好")
        assert 2.0 < dur < 4.0

    def test_english_text(self):
        dur = estimate_duration("hello world this is a test")
        assert dur > 0

    def test_speed_factor(self):
        t1 = estimate_duration("你好世界", speed=1.0)
        t2 = estimate_duration("你好世界", speed=2.0)
        assert t2 < t1  # faster speed → shorter duration

    def test_mixed_text(self):
        dur = estimate_duration("Hello 你好 world 世界")
        assert dur > 0


class TestFormatDuration:
    def test_zero(self):
        assert format_duration(0) == "0:00"

    def test_seconds_only(self):
        assert format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert format_duration(125) == "2:05"

    def test_large_value(self):
        result = format_duration(3661)
        assert "61:" in result  # 61 minutes, 1 second
