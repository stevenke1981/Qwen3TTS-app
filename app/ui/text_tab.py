"""Text-to-speech tab"""

from datetime import datetime

from PySide6 import QtCore
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..audio.exporter import AudioExporter
from ..audio.player import AudioPlayer
from ..core.drafts import load_drafts, save_drafts
from ..core.duration_estimator import estimate_duration, format_duration
from ..core.history import HistoryEntry
from ..core.presets import VoicePreset, load_presets, save_custom_preset
from ..core.recent_texts import add_recent, load_recent
from ..core.ssml import SSML_TAGS, strip_ssml
from .theme import make_secondary_button
from .waveform_widget import WaveformWidget


class _FindReplaceDialog(QDialog):
    """Simple find-and-replace dialog for the text input."""

    def __init__(self, text_edit: QTextEdit, parent=None):
        super().__init__(parent)
        self._editor = text_edit
        self.setWindowTitle("查找 & 取代")
        self.setMinimumWidth(380)

        form = QFormLayout()
        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("查找文字…")
        form.addRow("查找：", self._find_input)

        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("取代為…")
        form.addRow("取代為：", self._replace_input)

        btn_box = QDialogButtonBox()
        self._find_btn = btn_box.addButton("查找下一個", QDialogButtonBox.ActionRole)
        self._replace_btn = btn_box.addButton("取代", QDialogButtonBox.ActionRole)
        self._replace_all_btn = btn_box.addButton("全部取代", QDialogButtonBox.ActionRole)
        close_btn = btn_box.addButton(QDialogButtonBox.Close)

        self._find_btn.clicked.connect(self._on_find)
        self._replace_btn.clicked.connect(self._on_replace)
        self._replace_all_btn.clicked.connect(self._on_replace_all)
        close_btn.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btn_box)

        self._find_input.returnPressed.connect(self._on_find)

    def _on_find(self) -> None:
        term = self._find_input.text()
        if not term:
            return
        if not self._editor.find(term):
            # Wrap around
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self._editor.setTextCursor(cursor)
            self._editor.find(term)

    def _on_replace(self) -> None:
        term = self._find_input.text()
        replacement = self._replace_input.text()
        cursor = self._editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == term:
            cursor.insertText(replacement)
        self._on_find()

    def _on_replace_all(self) -> None:
        term = self._find_input.text()
        replacement = self._replace_input.text()
        if not term:
            return
        text = self._editor.toPlainText()
        count = text.count(term)
        if count == 0:
            QMessageBox.information(self, "查找", f"找不到「{term}」")
            return
        self._editor.setPlainText(text.replace(term, replacement))
        QMessageBox.information(self, "取代完成", f"已取代 {count} 處「{term}」→「{replacement}」")


class _TTSWorker(QtCore.QObject):
    """Background worker for TTS synthesis."""

    finished = QtCore.Signal(bytes)
    error = QtCore.Signal(str)

    def __init__(self, api_client, text, config):
        super().__init__()
        self._api_client = api_client
        self._text = text
        self._config = config

    def run(self):
        try:
            result = self._api_client.synthesize(self._text, self._config)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _BatchTTSWorker(QtCore.QObject):
    """Background worker for batch TTS synthesis (paragraph-by-paragraph)."""

    progress = QtCore.Signal(int, int)  # current, total
    item_done = QtCore.Signal(int, bytes)  # index, audio_data
    finished = QtCore.Signal(list)  # list of (text, audio_bytes)
    error = QtCore.Signal(str)

    def __init__(self, api_client, paragraphs: list[str], config):
        super().__init__()
        self._api_client = api_client
        self._paragraphs = paragraphs
        self._config = config

    def run(self):
        try:
            results = []
            total = len(self._paragraphs)
            for i, text in enumerate(self._paragraphs):
                audio = self._api_client.synthesize(text, self._config)
                results.append((text, audio))
                self.progress.emit(i + 1, total)
                self.item_done.emit(i, audio)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class TextTab(QWidget):
    def __init__(self, api_client, history_manager):
        super().__init__()
        self.api_client = api_client
        self.history_manager = history_manager
        self.audio_player = AudioPlayer()
        self.current_audio: bytes | None = None
        self._thread: QtCore.QThread | None = None
        self._pending_text: str = ""
        self._batch_results: list[tuple[str, bytes]] = []

        self._previous_audio: bytes | None = None  # A/B compare: previous result
        self.setAcceptDrops(True)
        self._setup_ui()
        self._load_presets()
        self._restore_draft()

        # Debounced auto-save: save draft 2s after last keystroke
        self._draft_timer = QtCore.QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(2000)
        self._draft_timer.timeout.connect(self._save_draft)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        input_group = QGroupBox("文字輸入")
        input_layout = QVBoxLayout(input_group)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("請輸入要合成的文字...")
        self.text_input.setMinimumHeight(130)
        self.text_input.textChanged.connect(self._on_text_changed)
        input_layout.addWidget(self.text_input)

        # ── Recent-texts + SSML toolbar row ──
        toolbar_row = QHBoxLayout()
        toolbar_row.setContentsMargins(0, 0, 0, 0)
        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("最近文字")
        self.recent_combo.setMinimumWidth(160)
        self.recent_combo.activated.connect(self._on_recent_selected)
        toolbar_row.addWidget(self.recent_combo)
        toolbar_row.addSpacing(8)
        for tag in SSML_TAGS[:4]:  # break, emphasis, prosody, phoneme
            btn = QPushButton(tag.label)
            btn.setToolTip(tag.description)
            btn.setMaximumWidth(70)
            btn.clicked.connect(lambda _=False, tpl=tag.template: self._insert_ssml(tpl))
            make_secondary_button(btn)
            toolbar_row.addWidget(btn)

        # ── Find & Replace button ──
        find_replace_btn = QPushButton("🔍 取代")
        find_replace_btn.setToolTip("查找並取代文字 (Ctrl+H)")
        find_replace_btn.setMaximumWidth(70)
        find_replace_btn.clicked.connect(self._on_find_replace)
        make_secondary_button(find_replace_btn)
        toolbar_row.addWidget(find_replace_btn)

        # ── Insert sample text button ──
        sample_btn = QPushButton("📝 範例")
        sample_btn.setToolTip("插入範例文字（方便快速測試）")
        sample_btn.setMaximumWidth(60)
        sample_btn.clicked.connect(self._on_insert_sample)
        make_secondary_button(sample_btn)
        toolbar_row.addWidget(sample_btn)

        toolbar_row.addStretch()
        input_layout.addLayout(toolbar_row)

        # Character count + duration hint row
        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        self.char_count_label = QLabel("0 字")
        self.char_count_label.setProperty("muted", "true")
        self.char_count_label.setToolTip("目前輸入的字元數")
        self.duration_label = QLabel("")
        self.duration_label.setProperty("muted", "true")
        hint_row.addWidget(self.duration_label)
        hint_row.addStretch()
        hint_row.addWidget(self.char_count_label)
        input_layout.addLayout(hint_row)

        layout.addWidget(input_group)

        params_group = QGroupBox("合成參數")
        params_layout = QHBoxLayout(params_group)

        for name, attr, lo, hi, val, fmt, tip in [
            ("語速",  "speed",  50, 200, 100, lambda v: f"{v/100:.1f}x", "調整合成語速 (0.5x–2.0x)"),
            ("音調",  "pitch",  50, 200, 100, lambda v: f"{v/100:.1f}x", "調整合成音調 (0.5x–2.0x)"),
            ("音量",  "volume",  0, 100, 100, lambda v: f"{v/100:.1f}",  "調整輸出音量 (0–1.0)"),
        ]:
            col = QVBoxLayout()
            lbl_name = QLabel(name)
            lbl_name.setToolTip(tip)
            col.addWidget(lbl_name)
            slider = QSlider(QtCore.Qt.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(val)
            slider.setToolTip(tip)
            val_label = QLabel(fmt(val))
            val_label.setProperty("muted", "true")
            slider.valueChanged.connect(lambda v, f=fmt, lbl=val_label: lbl.setText(f(v)))
            col.addWidget(slider)
            col.addWidget(val_label)
            params_layout.addLayout(col)
            setattr(self, f"{attr}_slider", slider)
            setattr(self, f"{attr}_label", val_label)

        layout.addWidget(params_group)

        # ── Preset row ──
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("預設組合："))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(140)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_row.addWidget(self.preset_combo)
        self.save_preset_btn = QPushButton("儲存為預設")
        self.save_preset_btn.setToolTip("將目前參數儲存為自訂預設")
        self.save_preset_btn.clicked.connect(self._on_save_preset)
        make_secondary_button(self.save_preset_btn)
        preset_row.addWidget(self.save_preset_btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # ── Waveform ──
        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        self.synthesize_btn = QPushButton("▶  合成")
        self.synthesize_btn.clicked.connect(self._on_synthesize)
        self.synthesize_btn.setToolTip("開始語音合成 (Ctrl+Enter)")
        button_layout.addWidget(self.synthesize_btn)

        self.batch_btn = QPushButton("📑  批次合成")
        self.batch_btn.clicked.connect(self._on_batch_synthesize)
        self.batch_btn.setToolTip("按段落批次合成並匯出 (每個段落一個音檔)")
        make_secondary_button(self.batch_btn)
        button_layout.addWidget(self.batch_btn)

        button_layout.addStretch()

        self.play_btn = QPushButton("▶  播放")
        self.play_btn.clicked.connect(self._on_play)
        self.play_btn.setEnabled(False)
        self.play_btn.setToolTip("播放 / 暫停合成音訊")
        make_secondary_button(self.play_btn)
        button_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("■  停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("停止播放")
        make_secondary_button(self.stop_btn)
        button_layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton("💾  匯出")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        self.export_btn.setToolTip("匯出音訊檔案 (Ctrl+S)")
        make_secondary_button(self.export_btn)
        button_layout.addWidget(self.export_btn)

        self.copy_path_btn = QPushButton("📋  複製路徑")
        self.copy_path_btn.clicked.connect(self._on_copy_audio_path)
        self.copy_path_btn.setEnabled(False)
        self.copy_path_btn.setToolTip("將最後匯出的音訊路徑複製到剪貼簿")
        make_secondary_button(self.copy_path_btn)
        button_layout.addWidget(self.copy_path_btn)

        layout.addLayout(button_layout)

        # ── A/B compare row ──
        ab_row = QHBoxLayout()
        ab_row.setContentsMargins(0, 0, 0, 0)
        self.ab_a_btn = QPushButton("🅰 上次")
        self.ab_a_btn.clicked.connect(self._play_a)
        self.ab_a_btn.setEnabled(False)
        make_secondary_button(self.ab_a_btn)
        self.ab_b_btn = QPushButton("🅱 本次")
        self.ab_b_btn.clicked.connect(self._play_b)
        self.ab_b_btn.setEnabled(False)
        make_secondary_button(self.ab_b_btn)
        ab_row.addWidget(QLabel("A/B 比較："))
        ab_row.addWidget(self.ab_a_btn)
        ab_row.addWidget(self.ab_b_btn)
        ab_row.addStretch()
        layout.addLayout(ab_row)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._on_synthesize)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._on_export)
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(self._on_find_replace)

    def _on_synthesize(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "請輸入要合成的文字")
            return

        if self._thread and self._thread.isRunning():
            return

        from ..api.qwen3_client import TTSConfig

        config = TTSConfig(
            speed=self.speed_slider.value() / 100,
            pitch=self.pitch_slider.value() / 100,
            volume=self.volume_slider.value() / 100,
        )

        self._pending_text = text
        self._pending_config = config
        self.synthesize_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self._thread = QtCore.QThread()
        self._worker = _TTSWorker(self.api_client, text, config)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_synthesis_done)
        self._worker.error.connect(self._on_synthesis_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_synthesis_done(self, audio_data: bytes):
        # A/B compare: push previous result
        if self.current_audio is not None:
            self._previous_audio = self.current_audio
            self.ab_a_btn.setEnabled(True)
        self.current_audio = audio_data
        self.ab_b_btn.setEnabled(True)

        # Save to recent-texts queue
        add_recent(self._pending_text)
        self._refresh_recent_combo()

        entry = HistoryEntry(
            id=self.history_manager.generate_id(),
            timestamp=datetime.now().isoformat(),
            operation="tts",
            text=self._pending_text,
            config={
                "speed": self._pending_config.speed,
                "pitch": self._pending_config.pitch,
                "volume": self._pending_config.volume,
            },
            audio_duration=AudioExporter.get_info(audio_data)["duration"],
        )
        self.history_manager.add(entry)

        self.waveform.set_audio(audio_data)
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.synthesize_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _on_synthesis_error(self, error: str):
        QMessageBox.critical(self, "錯誤", f"合成失敗：{error}")
        self.synthesize_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _on_text_changed(self):
        text = self.text_input.toPlainText()
        plain = strip_ssml(text)
        chars = len(plain)
        lines = plain.count("\n") + 1 if plain else 0
        words = len(plain.split()) if plain.strip() else 0
        self.char_count_label.setText(f"{chars} 字 | {lines} 行 | ~{words} 詞")
        # Duration estimate
        speed = self.speed_slider.value() / 100
        dur = estimate_duration(plain, speed)
        self.duration_label.setText(f"預估時長：{format_duration(dur)}" if dur > 0 else "")
        # Restart auto-save timer
        if hasattr(self, "_draft_timer"):
            self._draft_timer.start()

    def _on_play(self):
        if self.current_audio:
            if self.audio_player.is_playing():
                self.audio_player.pause()
                self.play_btn.setText("▶  繼續")
            else:
                self.audio_player.play(self.current_audio)
                self.play_btn.setText("⏸  暫停")

    def _on_stop(self):
        self.audio_player.stop()
        self.play_btn.setText("▶  播放")

    def _on_export(self):
        if not self.current_audio:
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "匯出音訊",
            "",
            "WAV 音訊 (*.wav);;MP3 音訊 (*.mp3);;所有檔案 (*.*)",
        )
        if path:
            try:
                if selected_filter == "MP3 音訊 (*.mp3)" or path.lower().endswith(".mp3"):
                    AudioExporter.to_mp3(self.current_audio, path)
                else:
                    AudioExporter.to_wav(self.current_audio, path)
                self._last_export_path = path
                self.copy_path_btn.setEnabled(True)
                QMessageBox.information(self, "成功", f"已匯出至：{path}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"匯出失敗：{str(e)}")

    def _on_copy_audio_path(self) -> None:
        """Copy the last exported audio file path to clipboard."""
        path = getattr(self, "_last_export_path", None)
        if path:
            QApplication.clipboard().setText(path)

    def _on_find_replace(self) -> None:
        """Open a Find & Replace dialog for the text input."""
        dialog = _FindReplaceDialog(self.text_input, self)
        dialog.exec()

    def _on_insert_sample(self) -> None:
        """Insert a short Chinese sample text for quick testing."""
        sample = (
            "春眠不覺曉，處處聞啼鳥。\n"
            "夜來風雨聲，花落知多少。\n\n"
            "人工智慧語音合成技術，讓文字化為聲音。\n"
            "Qwen3-TTS 支援中文、英文等多語言合成。"
        )
        self.text_input.setPlainText(sample)

    # ── Preset methods ──

    def _load_presets(self):
        """Populate preset combo box from built-in + custom presets."""
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("— 手動 —")
        for preset in load_presets():
            self.preset_combo.addItem(preset.name, userData=preset)
        self.preset_combo.blockSignals(False)

    def _on_preset_selected(self, index: int):
        if index <= 0:
            return
        preset: VoicePreset | None = self.preset_combo.currentData()
        if preset is None:
            return
        self.speed_slider.setValue(int(preset.speed * 100))
        self.pitch_slider.setValue(int(preset.pitch * 100))
        self.volume_slider.setValue(int(preset.volume * 100))

    def _on_save_preset(self):
        name, ok = QInputDialog.getText(self, "儲存預設", "請輸入預設名稱：")
        if not ok or not name.strip():
            return
        preset = VoicePreset(
            name=name.strip(),
            speed=self.speed_slider.value() / 100,
            pitch=self.pitch_slider.value() / 100,
            volume=self.volume_slider.value() / 100,
        )
        save_custom_preset(preset)
        self._load_presets()
        QMessageBox.information(self, "成功", f"已儲存預設「{name.strip()}」")

    # ── Batch TTS ──

    def _on_batch_synthesize(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "請輸入要合成的文字")
            return
        if self._thread and self._thread.isRunning():
            return

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) < 2:
            QMessageBox.information(
                self, "提示", "文字僅有一段，請直接使用「合成」。\n批次合成需以空行分隔段落。"
            )
            return

        out_dir = QFileDialog.getExistingDirectory(self, "選擇批次匯出資料夾")
        if not out_dir:
            return

        from ..api.qwen3_client import TTSConfig

        config = TTSConfig(
            speed=self.speed_slider.value() / 100,
            pitch=self.pitch_slider.value() / 100,
            volume=self.volume_slider.value() / 100,
        )

        self._batch_out_dir = out_dir
        self._batch_results = []
        self.synthesize_btn.setEnabled(False)
        self.batch_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(paragraphs))
        self.progress_bar.setValue(0)

        self._thread = QtCore.QThread()
        self._batch_worker = _BatchTTSWorker(self.api_client, paragraphs, config)
        self._batch_worker.moveToThread(self._thread)
        self._thread.started.connect(self._batch_worker.run)
        self._batch_worker.progress.connect(self._on_batch_progress)
        self._batch_worker.finished.connect(self._on_batch_done)
        self._batch_worker.error.connect(self._on_batch_error)
        self._batch_worker.finished.connect(self._thread.quit)
        self._batch_worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._batch_worker.deleteLater)
        self._thread.start()

    def _on_batch_done(self, results: list):
        import os

        for i, (text, audio) in enumerate(results):
            fname = os.path.join(self._batch_out_dir, f"part_{i + 1:03d}.wav")
            AudioExporter.to_wav(audio, fname)

        # Auto-concatenate all chunks into one file
        chunks = [audio for _, audio in results]
        concat_path = os.path.join(self._batch_out_dir, "all_concat.wav")
        try:
            from ..audio.concatenator import concatenate_to_file
            concatenate_to_file(chunks, concat_path, gap_ms=300)
        except Exception:
            pass  # non-critical

        self.synthesize_btn.setEnabled(True)
        self.batch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(
            self, "完成", f"已匯出 {len(results)} 段音訊至：\n{self._batch_out_dir}"
        )

    def _on_batch_error(self, error: str):
        self.synthesize_btn.setEnabled(True)
        self.batch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "錯誤", f"批次合成失敗：{error}")

    # ── Drag-and-drop ──

    def dragEnterEvent(self, event):  # noqa: N802
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path.lower().endswith((".txt", ".md", ".srt")):
                    try:
                        with open(path, encoding="utf-8") as f:
                            self.text_input.setPlainText(f.read())
                    except Exception:
                        pass
                    break
        elif mime.hasText():
            self.text_input.setPlainText(mime.text())

    # ── Auto-save drafts ──

    def _save_draft(self):
        text = self.text_input.toPlainText()
        drafts = load_drafts()
        drafts["text_tab"] = text
        save_drafts(drafts)

    def _restore_draft(self):
        drafts = load_drafts()
        text = drafts.get("text_tab", "")
        if text:
            self.text_input.setPlainText(text)
        self._refresh_recent_combo()

    # ── Batch progress percentage ──

    def _on_batch_progress(self, current: int, total: int):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        pct = int(current / total * 100) if total else 0
        self.progress_bar.setFormat(f"{current}/{total}  ({pct}%)")
        self.progress_bar.setTextVisible(True)

    # ── A/B compare helpers ──

    def _play_a(self):
        if self._previous_audio:
            self.audio_player.play(self._previous_audio)

    def _play_b(self):
        if self.current_audio:
            self.audio_player.play(self.current_audio)

    # ── SSML insert ──

    def _insert_ssml(self, template: str):
        cursor = self.text_input.textCursor()
        selected = cursor.selectedText()
        if selected:
            text = template.replace("{text}", selected)
        else:
            text = template
        cursor.insertText(text)

    # ── Recent texts ──

    def _refresh_recent_combo(self):
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        for item in load_recent():
            display = item[:40] + "…" if len(item) > 40 else item
            self.recent_combo.addItem(display, userData=item)
        self.recent_combo.blockSignals(False)

    def _on_recent_selected(self, index: int):
        text = self.recent_combo.itemData(index)
        if text:
            self.text_input.setPlainText(text)
