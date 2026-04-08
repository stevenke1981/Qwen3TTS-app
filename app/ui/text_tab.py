"""Text-to-speech tab"""

from datetime import datetime

from PySide6 import QtCore
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
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
from ..core.history import HistoryEntry
from ..core.presets import VoicePreset, load_presets, save_custom_preset
from .theme import make_secondary_button
from .waveform_widget import WaveformWidget


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

        # Character count hint row
        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        self.char_count_label = QLabel("0 字")
        self.char_count_label.setProperty("muted", "true")
        self.char_count_label.setToolTip("目前輸入的字元數")
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

        layout.addLayout(button_layout)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._on_synthesize)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._on_export)

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
        self.current_audio = audio_data

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
        chars = len(text)
        lines = text.count("\n") + 1 if text else 0
        words = len(text.split()) if text.strip() else 0
        self.char_count_label.setText(f"{chars} 字 | {lines} 行 | ~{words} 詞")
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

        path, _ = QFileDialog.getSaveFileName(
            self, "匯出音訊", "", "WAV 音訊 (*.wav);;所有檔案 (*.*)"
        )
        if path:
            try:
                AudioExporter.to_wav(self.current_audio, path)
                QMessageBox.information(self, "成功", f"已匯出至：{path}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"匯出失敗：{str(e)}")

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
        self._batch_worker.progress.connect(
            lambda cur, total: self.progress_bar.setValue(cur)
        )
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
