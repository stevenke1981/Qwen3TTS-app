"""Minimal i18n string table for the application UI.

Usage::

    from app.core.i18n import t
    label = t("synthesize")  # → "▶  合成" (zh-TW) or "▶  Synthesize" (en)

The active locale can be switched with ``set_locale("en")``.
"""

from __future__ import annotations

# ── String tables ─────────────────────────────────────────────────────────────

_STRINGS: dict[str, dict[str, str]] = {
    "zh-TW": {
        # ── Common ──
        "app_title": "Qwen3-TTS 語音合成",
        "ready": "就緒",
        "warning": "警告",
        "error": "錯誤",
        "success": "成功",
        "cancel": "取消",
        "ok": "確定",
        "save": "儲存",
        "export": "匯出",
        "copy": "複製",
        "delete": "刪除",
        "clear": "清除",
        "close": "關閉",
        # ── TextTab ──
        "text_input_placeholder": "請輸入要合成的文字...",
        "synthesize": "▶  合成",
        "batch_synthesize": "📑  批次合成",
        "play": "▶  播放",
        "pause": "⏸  暫停",
        "resume": "▶  繼續",
        "stop": "■  停止",
        "export_audio": "💾  匯出",
        "text_input_group": "文字輸入",
        "params_group": "合成參數",
        "speed": "語速",
        "pitch": "音調",
        "volume": "音量",
        "preset_label": "預設組合：",
        "save_preset": "儲存為預設",
        "empty_text_warning": "請輸入要合成的文字",
        "synthesis_failed": "合成失敗：{error}",
        "char_count": "{chars} 字 | {lines} 行 | ~{words} 詞",
        "estimated_duration": "預估時長：{duration}",
        "recent_texts": "最近文字",
        "ssml_toolbar": "SSML 標記",
        "concat_all": "🔗  拼接全部",
        "ab_compare": "A/B 比較",
        "switch_a": "🅰 上次",
        "switch_b": "🅱 本次",
        # ── CloneTab ──
        "clone_voice": "克隆語音",
        "text_ref_mode": "文字參考",
        "audio_ref_mode": "音檔參考",
        "ref_source": "參考來源",
        "ref_text_hint": "參考文字（將用相同音色朗讀）：",
        "ref_text_placeholder": "請輸入參考文字...",
        "ref_audio_hint": "參考音檔（將克隆該音色）：",
        "no_file_selected": "未選擇檔案",
        "select_audio": "選擇音檔",
        "audio_format_hint": "支援格式：WAV, MP3（建議時長 5-30 秒）",
        # ── EditTab ──
        "input_text_placeholder": "請輸入要處理的文字...",
        "process": "處理",
        "process_result": "處理結果",
        "send_to_tts": "送往文字合成",
        "send_to_clone": "送往語音克隆",
        "quick_actions": "快速操作",
        "model_info": "模型資訊",
        "test_llm": "測試 LLM 連線",
        "processing_mode": "處理模式：",
        # ── ASR Tab ──
        "asr_title": "語音辨識",
        # ── History Tab ──
        "history_title": "歷史記錄",
        "retry": "重試",
        # ── Settings Tab ──
        "settings_title": "設定",
        "save_settings": "💾  儲存設定",
        "test_qwen3": "🔌  測試 Qwen3 連線",
        "test_asr": "🔌  測試 ASR API",
        "export_config": "📤  匯出設定",
        "import_config": "📥  匯入設定",
        # ── Tray ──
        "show_window": "顯示主視窗",
        "quit": "結束",
        "minimized_to_tray": "應用程式已最小化至系統列",
        # ── Log viewer ──
        "view_log": "檢視日誌",
        "log_viewer_title": "應用程式日誌",
    },
    "en": {
        "app_title": "Qwen3-TTS Voice Synthesis",
        "ready": "Ready",
        "warning": "Warning",
        "error": "Error",
        "success": "Success",
        "cancel": "Cancel",
        "ok": "OK",
        "save": "Save",
        "export": "Export",
        "copy": "Copy",
        "delete": "Delete",
        "clear": "Clear",
        "close": "Close",
        "text_input_placeholder": "Enter text to synthesize...",
        "synthesize": "▶  Synthesize",
        "batch_synthesize": "📑  Batch",
        "play": "▶  Play",
        "pause": "⏸  Pause",
        "resume": "▶  Resume",
        "stop": "■  Stop",
        "export_audio": "💾  Export",
        "text_input_group": "Text Input",
        "params_group": "Synthesis Parameters",
        "speed": "Speed",
        "pitch": "Pitch",
        "volume": "Volume",
        "preset_label": "Preset:",
        "save_preset": "Save Preset",
        "empty_text_warning": "Please enter text to synthesize",
        "synthesis_failed": "Synthesis failed: {error}",
        "char_count": "{chars} chars | {lines} lines | ~{words} words",
        "estimated_duration": "Est. duration: {duration}",
        "recent_texts": "Recent Texts",
        "ssml_toolbar": "SSML Tags",
        "concat_all": "🔗  Concat All",
        "ab_compare": "A/B Compare",
        "switch_a": "🅰 Previous",
        "switch_b": "🅱 Current",
        "clone_voice": "Clone Voice",
        "text_ref_mode": "Text Reference",
        "audio_ref_mode": "Audio Reference",
        "ref_source": "Reference Source",
        "ref_text_hint": "Reference text (same voice):",
        "ref_text_placeholder": "Enter reference text...",
        "ref_audio_hint": "Reference audio (clone voice):",
        "no_file_selected": "No file selected",
        "select_audio": "Select Audio",
        "audio_format_hint": "Formats: WAV, MP3 (5-30 sec recommended)",
        "input_text_placeholder": "Enter text to process...",
        "process": "Process",
        "process_result": "Result",
        "send_to_tts": "Send to TTS",
        "send_to_clone": "Send to Clone",
        "quick_actions": "Quick Actions",
        "model_info": "Model Info",
        "test_llm": "Test LLM Connection",
        "processing_mode": "Mode:",
        "asr_title": "Speech Recognition",
        "history_title": "History",
        "retry": "Retry",
        "settings_title": "Settings",
        "save_settings": "💾  Save Settings",
        "test_qwen3": "🔌  Test Qwen3",
        "test_asr": "🔌  Test ASR API",
        "export_config": "📤  Export Config",
        "import_config": "📥  Import Config",
        "show_window": "Show Window",
        "quit": "Quit",
        "minimized_to_tray": "App minimized to system tray",
        "view_log": "View Log",
        "log_viewer_title": "Application Log",
    },
}

# ── Active locale ─────────────────────────────────────────────────────────────

_current_locale: str = "zh-TW"


def set_locale(locale: str) -> None:
    """Switch the active locale (e.g. ``'zh-TW'`` or ``'en'``)."""
    global _current_locale  # noqa: PLW0603
    if locale in _STRINGS:
        _current_locale = locale


def get_locale() -> str:
    """Return the current active locale."""
    return _current_locale


def available_locales() -> list[str]:
    """Return all registered locale codes."""
    return list(_STRINGS.keys())


def t(key: str, **kwargs: str) -> str:
    """Translate *key* to the active locale.

    Supports ``str.format()`` interpolation via **kwargs**.  Falls back to
    ``zh-TW`` if the key is missing in the active locale, then to the raw key.
    """
    table = _STRINGS.get(_current_locale, _STRINGS["zh-TW"])
    text = table.get(key) or _STRINGS["zh-TW"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
