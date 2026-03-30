"""ASR Tab — Qwen3-ASR speech recognition + YouTube/URL subtitle generation.

Features
--------
* Local audio/video file transcription (WAV · MP3 · M4A · FLAC · OGG · MP4 · MKV)
* Online video URL download via yt-dlp + ffmpeg, then ASR
* Language selector (Auto-detect / 30+ languages)
* Model selector (Qwen3-ASR-0.6B · 1.7B)
* Timestamped subtitle export (SRT · VTT · TXT)
* Real-time progress updates from the subprocess worker
* Runs ASR in venv-asr via QThread so the UI stays responsive
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QClipboard, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QTextEdit, QPushButton, QComboBox, QCheckBox,
    QProgressBar, QFileDialog, QMessageBox, QSizePolicy,
    QRadioButton, QButtonGroup, QApplication, QFrame,
)

from ..api.asr_client import ASRClient, ASRResult
from .theme import (
    make_secondary_button, COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING,
    COLOR_MUTED, FONT_SIZE_SM, FONT_SIZE_BASE,
)

# ── Language options ───────────────────────────────────────────────────────────
_LANGUAGES = [
    ("自動偵測",         "auto"),
    ("中文 (普通話)",    "Chinese"),
    ("廣東話",           "Cantonese"),
    ("英文",             "English"),
    ("日文",             "Japanese"),
    ("韓文",             "Korean"),
    ("法文",             "French"),
    ("德文",             "German"),
    ("西班牙文",         "Spanish"),
    ("葡萄牙文",         "Portuguese"),
    ("阿拉伯文",         "Arabic"),
    ("俄文",             "Russian"),
    ("印度文 (Hindi)",   "Hindi"),
    ("泰文",             "Thai"),
    ("越南文",           "Vietnamese"),
    ("印尼文",           "Indonesian"),
    ("土耳其文",         "Turkish"),
    ("義大利文",         "Italian"),
    ("荷蘭文",           "Dutch"),
    ("波蘭文",           "Polish"),
]

# ── Model options ──────────────────────────────────────────────────────────────
_MODELS = [
    ("Qwen3-ASR-0.6B  （快速）",  "Qwen/Qwen3-ASR-0.6B"),
    ("Qwen3-ASR-1.7B  （精準）",  "Qwen/Qwen3-ASR-1.7B"),
]

# ── Audio / video extensions accepted by file picker ──────────────────────────
_AUDIO_FILTER = (
    "音訊 / 影片檔案 (*.wav *.mp3 *.m4a *.flac *.ogg *.opus *.mp4 *.mkv *.webm *.avi);;"
    "所有檔案 (*)"
)


# ─── Background worker ────────────────────────────────────────────────────────

class _ASRWorker(QObject):
    """Runs ASRClient.transcribe() in a QThread.

    Signals
    -------
    progress(str)   Human-readable Chinese progress message.
    finished(ASRResult)
    error(str)
    """

    progress = Signal(str)
    finished = Signal(object)   # ASRResult
    error    = Signal(str)

    def __init__(
        self,
        client: ASRClient,
        source: str,
        source_type: str,    # "file" | "url"
        model_id: str,
        language: str,
        timestamps: bool,
    ) -> None:
        super().__init__()
        self._client      = client
        self._source      = source
        self._source_type = source_type
        self._model_id    = model_id
        self._language    = language
        self._timestamps  = timestamps

    def run(self) -> None:
        try:
            result = self._client.transcribe(
                source          = self._source,
                source_type     = self._source_type,
                model_id        = self._model_id,
                language        = self._language,
                timestamps      = self._timestamps,
                progress_callback = self.progress.emit,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ─── ASR Tab ──────────────────────────────────────────────────────────────────

class ASRTab(QWidget):
    """Speech-recognition + subtitle generation tab."""

    def __init__(self, asr_client: ASRClient) -> None:
        super().__init__()
        self.asr_client: ASRClient = asr_client
        self._result: ASRResult | None = None
        self._thread: QThread | None = None
        self._worker: _ASRWorker | None = None

        self._setup_ui()
        self._connect_signals()
        self._refresh_availability()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        root.addWidget(self._build_env_banner())
        root.addWidget(self._build_source_group())
        root.addWidget(self._build_options_group())
        root.addWidget(self._build_action_bar())
        root.addWidget(self._build_output_group())

    # ── Environment banner ────────────────────────────────────────────────────

    def _build_env_banner(self) -> QLabel:
        self.env_banner = QLabel()
        self.env_banner.setWordWrap(True)
        self.env_banner.setAlignment(Qt.AlignCenter)
        self.env_banner.setFixedHeight(28)
        self.env_banner.setStyleSheet(
            f"font-size: {FONT_SIZE_SM}px; border-radius: 4px; padding: 2px 8px;"
        )
        return self.env_banner

    # ── Source group ──────────────────────────────────────────────────────────

    def _build_source_group(self) -> QGroupBox:
        grp = QGroupBox("來源")
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(8)

        # Radio buttons
        radio_row = QHBoxLayout()
        self._radio_grp = QButtonGroup(self)
        self.rb_file = QRadioButton("本地檔案")
        self.rb_url  = QRadioButton("線上影片 URL（YouTube / Bilibili…）")
        self.rb_file.setChecked(True)
        for rb in (self.rb_file, self.rb_url):
            self._radio_grp.addButton(rb)
            radio_row.addWidget(rb)
        radio_row.addStretch()
        vbox.addLayout(radio_row)

        # File row
        self.file_row = QWidget()
        file_layout = QHBoxLayout(self.file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(6)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("點選「瀏覽」選擇音訊 / 影片檔案…")
        self.file_path_edit.setReadOnly(True)
        self.browse_btn = QPushButton("📁  瀏覽")
        make_secondary_button(self.browse_btn)
        self.browse_btn.setFixedWidth(100)
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.browse_btn)
        vbox.addWidget(self.file_row)

        # URL row
        self.url_row = QWidget()
        url_layout = QHBoxLayout(self.url_row)
        url_layout.setContentsMargins(0, 0, 0, 0)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(
            "例： https://www.youtube.com/watch?v=xxxxx"
        )
        url_layout.addWidget(self.url_edit)
        self.url_row.setVisible(False)
        vbox.addWidget(self.url_row)

        return grp

    # ── Options group ─────────────────────────────────────────────────────────

    def _build_options_group(self) -> QGroupBox:
        grp = QGroupBox("辨識選項")
        row = QHBoxLayout(grp)
        row.setSpacing(20)

        # Language
        lang_col = QVBoxLayout()
        lang_col.setSpacing(4)
        lang_col.addWidget(QLabel("語言"))
        self.lang_combo = QComboBox()
        for label, code in _LANGUAGES:
            self.lang_combo.addItem(label, userData=code)
        self.lang_combo.setMinimumWidth(180)
        lang_col.addWidget(self.lang_combo)
        row.addLayout(lang_col)

        # Model
        model_col = QVBoxLayout()
        model_col.setSpacing(4)
        model_col.addWidget(QLabel("模型"))
        self.model_combo = QComboBox()
        for label, mid in _MODELS:
            self.model_combo.addItem(label, userData=mid)
        self.model_combo.setMinimumWidth(230)
        model_col.addWidget(self.model_combo)
        row.addLayout(model_col)

        # Timestamps checkbox
        ts_col = QVBoxLayout()
        ts_col.setSpacing(4)
        ts_col.addWidget(QLabel("時間軸"))
        self.ts_check = QCheckBox("產生時間戳記（時間軸字幕）")
        self.ts_check.setChecked(True)
        self.ts_check.setToolTip(
            "啟用 Qwen3-ForcedAligner-0.6B 進行詞語級別時間對齊\n"
            "（需要額外約 500 MB）"
        )
        ts_col.addWidget(self.ts_check)
        row.addLayout(ts_col)

        row.addStretch()
        return grp

    # ── Action bar + progress ─────────────────────────────────────────────────

    def _build_action_bar(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("🎙  開始辨識")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setShortcut("Ctrl+Return")
        self.start_btn.setToolTip("開始語音辨識  Ctrl+Enter")

        self.cancel_btn = QPushButton("✕  取消")
        make_secondary_button(self.cancel_btn)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedWidth(90)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        vbox.addLayout(btn_row)

        # Progress bar + stage label
        prog_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)          # indeterminate
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.stage_label = QLabel("")
        self.stage_label.setStyleSheet(
            f"color: {COLOR_MUTED}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )

        prog_row.addWidget(self.progress_bar)
        prog_row.addWidget(self.stage_label)
        vbox.addLayout(prog_row)

        return container

    # ── Output group ──────────────────────────────────────────────────────────

    def _build_output_group(self) -> QGroupBox:
        grp = QGroupBox("辨識結果")
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(6)

        # Detected language chip
        info_row = QHBoxLayout()
        lang_lbl = QLabel("偵測語言：")
        lang_lbl.setStyleSheet(
            f"color: {COLOR_MUTED}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )
        self.detected_lang_lbl = QLabel("—")
        self.detected_lang_lbl.setStyleSheet(
            f"color: {COLOR_SUCCESS}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )
        seg_lbl = QLabel("  片段數：")
        seg_lbl.setStyleSheet(
            f"color: {COLOR_MUTED}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )
        self.seg_count_lbl = QLabel("—")
        self.seg_count_lbl.setStyleSheet(
            f"color: {COLOR_MUTED}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )
        info_row.addWidget(lang_lbl)
        info_row.addWidget(self.detected_lang_lbl)
        info_row.addWidget(seg_lbl)
        info_row.addWidget(self.seg_count_lbl)
        info_row.addStretch()
        vbox.addLayout(info_row)

        # Output text area
        self.output_edit = QTextEdit()
        self.output_edit.setPlaceholderText("辨識結果將顯示在這裡…")
        self.output_edit.setReadOnly(False)
        self.output_edit.setMinimumHeight(180)
        vbox.addWidget(self.output_edit)

        # Export buttons
        export_row = QHBoxLayout()
        self.copy_btn = QPushButton("📋  複製")
        self.export_txt_btn = QPushButton("💾  匯出 TXT")
        self.export_srt_btn = QPushButton("🎬  匯出 SRT")
        self.export_vtt_btn = QPushButton("🌐  匯出 VTT")
        for btn in (self.copy_btn, self.export_txt_btn,
                    self.export_srt_btn, self.export_vtt_btn):
            make_secondary_button(btn)
            btn.setEnabled(False)
            export_row.addWidget(btn)
        export_row.addStretch()

        self.copy_btn.setToolTip("複製純文字")
        self.export_txt_btn.setToolTip("匯出純文字 .txt")
        self.export_srt_btn.setToolTip("匯出 SRT 時間軸字幕（影片播放器用）")
        self.export_vtt_btn.setToolTip("匯出 WebVTT 字幕（網頁用）")

        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(self._on_copy)

        vbox.addLayout(export_row)
        return grp

    # ── Signals ───────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self.rb_file.toggled.connect(self._on_source_toggled)
        self.browse_btn.clicked.connect(self._on_browse)
        self.start_btn.clicked.connect(self._on_start)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.copy_btn.clicked.connect(self._on_copy)
        self.export_txt_btn.clicked.connect(lambda: self._on_export("txt"))
        self.export_srt_btn.clicked.connect(lambda: self._on_export("srt"))
        self.export_vtt_btn.clicked.connect(lambda: self._on_export("vtt"))

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_source_toggled(self, file_mode: bool) -> None:
        self.file_row.setVisible(file_mode)
        self.url_row.setVisible(not file_mode)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇音訊 / 影片檔案", "", _AUDIO_FILTER
        )
        if path:
            self.file_path_edit.setText(path)

    def _on_start(self) -> None:
        # Validate source
        if self.rb_file.isChecked():
            source = self.file_path_edit.text().strip()
            source_type = "file"
            if not source:
                QMessageBox.warning(self, "缺少來源", "請先選擇一個音訊 / 影片檔案。")
                return
            if not Path(source).exists():
                QMessageBox.warning(self, "檔案不存在", f"找不到檔案：\n{source}")
                return
        else:
            source = self.url_edit.text().strip()
            source_type = "url"
            if not source:
                QMessageBox.warning(self, "缺少 URL", "請輸入影片網址。")
                return
            if not re.match(r"^https?://", source):
                QMessageBox.warning(self, "網址格式錯誤", "請輸入有效的 http:// 或 https:// 網址。")
                return

        if not self.asr_client.is_available():
            QMessageBox.critical(
                self, "venv-asr 未就緒",
                "ASR 環境（venv-asr）尚未安裝。\n\n"
                "請在專案根目錄執行：\n"
                "  Windows：setup_asr.bat\n"
                "  Linux/Mac：bash setup_asr.sh",
            )
            return

        model_id = self.model_combo.currentData()
        language = self.lang_combo.currentData()
        timestamps = self.ts_check.isChecked()

        self._set_busy(True)
        self._clear_output()
        self.stage_label.setText("準備中…")

        # Create worker + thread
        self._thread = QThread(self)
        self._worker = _ASRWorker(
            client      = self.asr_client,
            source      = source,
            source_type = source_type,
            model_id    = model_id,
            language    = language,
            timestamps  = timestamps,
        )
        self._worker.moveToThread(self._thread)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_cancel(self) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            self._thread.wait(2000)
        self._set_busy(False)
        self.stage_label.setText("已取消")

    def _on_progress(self, label: str) -> None:
        self.stage_label.setText(label)

    def _on_finished(self, result: ASRResult) -> None:
        self._result = result
        self._set_busy(False)
        self.stage_label.setText(
            f"✓ 完成  ·  偵測語言：{result.language}  ·  {len(result.segments)} 個片段"
        )
        self.stage_label.setStyleSheet(
            f"color: {COLOR_SUCCESS}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )
        self.detected_lang_lbl.setText(result.language or "—")
        self.seg_count_lbl.setText(str(len(result.segments)) if result.segments else "0（無時間戳）")

        # Display in output area
        if result.segments:
            lines = []
            for seg in result.segments:
                start = _fmt_display_time(seg.start)
                end   = _fmt_display_time(seg.end)
                lines.append(f"[{start} → {end}]  {seg.text}")
            self.output_edit.setPlainText("\n".join(lines))
        else:
            self.output_edit.setPlainText(result.text)

        for btn in (self.copy_btn, self.export_txt_btn,
                    self.export_srt_btn, self.export_vtt_btn):
            btn.setEnabled(True)
        # Disable SRT/VTT if no segments
        has_seg = bool(result.segments)
        self.export_srt_btn.setEnabled(has_seg)
        self.export_vtt_btn.setEnabled(has_seg)

    def _on_error(self, msg: str) -> None:
        self._set_busy(False)
        self.stage_label.setText("❌ 發生錯誤")
        self.stage_label.setStyleSheet(
            f"color: {COLOR_ERROR}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )
        short = msg[:1200] if len(msg) > 1200 else msg
        QMessageBox.critical(self, "ASR 錯誤", short)

    # ── Export handlers ───────────────────────────────────────────────────────

    def _on_copy(self) -> None:
        if self._result is None:
            return
        QApplication.clipboard().setText(self._result.to_txt())
        self.stage_label.setText("已複製到剪貼簿")

    def _on_export(self, fmt: str) -> None:
        if self._result is None:
            return

        ext_map   = {"txt": ".txt", "srt": ".srt", "vtt": ".vtt"}
        filt_map  = {
            "txt": "純文字 (*.txt)",
            "srt": "SRT 字幕 (*.srt)",
            "vtt": "WebVTT 字幕 (*.vtt)",
        }
        default_name = f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext_map[fmt]}"

        path, _ = QFileDialog.getSaveFileName(
            self, f"匯出 {fmt.upper()}", default_name, filt_map[fmt]
        )
        if not path:
            return

        content_map = {
            "txt": self._result.to_txt,
            "srt": self._result.to_srt,
            "vtt": self._result.to_vtt,
        }
        content = content_map[fmt]()

        try:
            Path(path).write_text(content, encoding="utf-8")
            self.stage_label.setText(f"✓ 已儲存 {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "儲存失敗", str(exc))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool) -> None:
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setVisible(busy)
        self.progress_bar.setVisible(busy)
        if not busy:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
        else:
            self.progress_bar.setRange(0, 0)

    def _clear_output(self) -> None:
        self._result = None
        self.output_edit.clear()
        self.detected_lang_lbl.setText("—")
        self.seg_count_lbl.setText("—")
        self.stage_label.setStyleSheet(
            f"color: {COLOR_MUTED}; font-size: {FONT_SIZE_SM}px; background: transparent;"
        )
        for btn in (self.copy_btn, self.export_txt_btn,
                    self.export_srt_btn, self.export_vtt_btn):
            btn.setEnabled(False)

    def _refresh_availability(self) -> None:
        avail = self.asr_client.is_available()
        if avail:
            self.env_banner.setText("● venv-asr 已就緒")
            self.env_banner.setStyleSheet(
                f"font-size: {FONT_SIZE_SM}px; border-radius: 4px; padding: 2px 8px;"
                f"background: #1a3d1a; color: {COLOR_SUCCESS};"
            )
        else:
            self.env_banner.setText(
                "⚠ venv-asr 未安裝 — 請先執行 setup_asr.bat（Windows）或 bash setup_asr.sh（Linux/Mac）"
            )
            self.env_banner.setStyleSheet(
                f"font-size: {FONT_SIZE_SM}px; border-radius: 4px; padding: 2px 8px;"
                f"background: #3d3010; color: {COLOR_WARNING};"
            )
        self.start_btn.setEnabled(avail)


# ─── Time display helper ──────────────────────────────────────────────────────

def _fmt_display_time(seconds: float) -> str:
    """Format ``123.456`` → ``2:03.456`` for compact display in the text area."""
    ms = int(round((seconds % 1) * 1000))
    s  = int(seconds) % 60
    m  = int(seconds) // 60
    if m:
        return f"{m}:{s:02d}.{ms:03d}"
    return f"{s}.{ms:03d}"
