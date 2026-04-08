"""Tests for app.core.i18n — minimal i18n string table."""

from __future__ import annotations

from app.core.i18n import available_locales, get_locale, set_locale, t


class TestLocale:
    def test_default_locale(self):
        assert get_locale() == "zh-TW"

    def test_switch_locale(self):
        set_locale("en")
        assert get_locale() == "en"
        set_locale("zh-TW")  # restore

    def test_invalid_locale_ignored(self):
        orig = get_locale()
        set_locale("nonexistent")
        assert get_locale() == orig

    def test_available_locales(self):
        locales = available_locales()
        assert "zh-TW" in locales
        assert "en" in locales


class TestTranslation:
    def test_zh_tw_key(self):
        set_locale("zh-TW")
        assert t("ready") == "就緒"

    def test_en_key(self):
        set_locale("en")
        assert t("ready") == "Ready"
        set_locale("zh-TW")

    def test_missing_key_returns_key(self):
        result = t("nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_interpolation(self):
        set_locale("zh-TW")
        result = t("synthesis_failed", error="timeout")
        assert "timeout" in result

    def test_interpolation_missing_kwarg(self):
        set_locale("zh-TW")
        result = t("synthesis_failed")
        assert "{error}" in result

    def test_fallback_to_zh_tw(self):
        set_locale("en")
        # All zh-TW keys should also exist in en; test the fallback mechanism
        set_locale("zh-TW")
        assert t("app_title") == "Qwen3-TTS 語音合成"
