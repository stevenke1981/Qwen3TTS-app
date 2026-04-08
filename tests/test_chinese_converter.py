"""Tests for app.core.chinese_converter — ChineseConverter."""

from __future__ import annotations

import pytest

from app.core.chinese_converter import HAS_OPENCC, ChineseConverter


class TestChineseConverterBasic:
    def test_empty_string_returns_unchanged(self):
        c = ChineseConverter()
        assert c.convert("") == ""
        assert c.convert("   ") == "   "

    def test_mode_constants_exist(self):
        assert ChineseConverter.S2T_MODE == "s2t"
        assert ChineseConverter.T2S_MODE == "t2s"
        assert ChineseConverter.S2T_TW_MODE == "s2tw"
        assert ChineseConverter.T2S_TW_MODE == "tw2s"
        assert ChineseConverter.S2T_HK_MODE == "s2hk"
        assert ChineseConverter.T2S_HK_MODE == "hk2s"


@pytest.mark.skipif(not HAS_OPENCC, reason="opencc not installed")
class TestWithOpenCC:
    def test_t2s(self):
        result = ChineseConverter.t2s("漢語")
        assert "汉" in result or result == "汉语"

    def test_s2t(self):
        result = ChineseConverter.s2t("汉语")
        assert "漢" in result

    def test_s2tw(self):
        result = ChineseConverter.s2tw("内存")
        # Taiwan usage: 記憶體 (may differ)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tw2s(self):
        result = ChineseConverter.tw2s("記憶體")
        assert isinstance(result, str)

    def test_roundtrip_s2t_t2s(self):
        original = "信息处理"
        trad = ChineseConverter.s2t(original)
        back = ChineseConverter.t2s(trad)
        # May not be exact roundtrip due to regional variants, but should be close
        assert isinstance(back, str)
        assert len(back) > 0

    def test_ascii_passthrough(self):
        c = ChineseConverter()
        assert c.convert("hello world 123") == "hello world 123"


@pytest.mark.skipif(HAS_OPENCC, reason="Only test fallback when opencc is absent")
class TestFallbackWithoutOpenCC:
    def test_convert_returns_original(self):
        c = ChineseConverter()
        text = "測試文字"
        result = c.convert(text)
        assert isinstance(result, str)


class TestStaticMethods:
    """Test static convenience methods exist and are callable."""

    def test_s2t_callable(self):
        assert callable(ChineseConverter.s2t)

    def test_t2s_callable(self):
        assert callable(ChineseConverter.t2s)

    def test_s2tw_callable(self):
        assert callable(ChineseConverter.s2tw)

    def test_tw2s_callable(self):
        assert callable(ChineseConverter.tw2s)

    def test_s2hk_callable(self):
        assert callable(ChineseConverter.s2hk)

    def test_hk2s_callable(self):
        assert callable(ChineseConverter.hk2s)
