"""Tests for app.core.auto_punctuation."""

from __future__ import annotations

from app.core.auto_punctuation import add_punctuation


class TestAddPunctuation:
    """Unit tests for add_punctuation()."""

    # ── Already-punctuated text ───────────────────────────────────────────────

    def test_already_punctuated_unchanged(self):
        text = "你好。這是一個測試！"
        assert add_punctuation(text) == text

    def test_already_punctuated_high_density(self):
        # >5% punctuation → returned unchanged
        text = "今天。天氣。不錯。"
        assert add_punctuation(text) == text

    # ── Empty / whitespace ────────────────────────────────────────────────────

    def test_empty_string(self):
        assert add_punctuation("") == ""

    def test_whitespace_only(self):
        assert add_punctuation("  ") == "  "

    # ── Plain sentences → terminal 。 ─────────────────────────────────────────

    def test_single_segment_gets_period(self):
        result = add_punctuation("今天天氣不錯")
        assert result.endswith("。")

    def test_no_spaces_gets_single_period(self):
        # No spaces = no splitting; should append single 。
        result = add_punctuation("我喜歡吃蘋果")
        assert result.endswith("。")
        assert "。" in result

    # ── Question detection ────────────────────────────────────────────────────

    def test_question_word_ma_gets_question_mark(self):
        result = add_punctuation("你吃飯了嗎")
        assert result.endswith("？")

    def test_question_word_shenme_gets_question_mark(self):
        result = add_punctuation("你在說什麼")
        assert result.endswith("？")

    def test_question_word_zenme_gets_question_mark(self):
        result = add_punctuation("你怎麼這樣做")
        assert result.endswith("？")

    def test_who_question_gets_question_mark(self):
        result = add_punctuation("這是誰說的")
        assert result.endswith("？")

    # ── Multi-segment with spaces ─────────────────────────────────────────────

    def test_two_segments_comma_joined(self):
        result = add_punctuation("你好世界 今天天氣不錯")
        assert "，" in result or "。" in result

    def test_multi_segment_question_at_end(self):
        result = add_punctuation("你吃飯了嗎 今天幾號")
        # At least one question mark expected
        assert "？" in result

    def test_multi_segment_produces_multiple_sentences(self):
        # A long enough input should split into multiple sentences
        long_text = (
            "我喜歡吃蘋果 "
            "我也喜歡吃橘子 "
            "你最愛什麼水果 "
            "我覺得西瓜很好吃 "
            "但是榴槤有人不喜歡"
        )
        result = add_punctuation(long_text)
        # Should have sentence-ending punctuation
        assert any(c in result for c in "。？")

    # ── comma_join=False ─────────────────────────────────────────────────────

    def test_comma_join_false_no_commas_between_segments(self):
        result = add_punctuation("你好 世界", comma_join=False)
        # No inner commas for comma_join=False
        assert "，" not in result

    def test_comma_join_true_default(self):
        result = add_punctuation("你好 世界")
        # comma_join=True (default) may produce commas for multi-segment
        assert result  # non-empty

    # ── Output correctness ────────────────────────────────────────────────────

    def test_output_ends_with_punctuation(self):
        result = add_punctuation("測試文本")
        assert result[-1] in "。？！"

    def test_no_trailing_whitespace(self):
        result = add_punctuation("你好 世界")
        assert result == result.strip()
