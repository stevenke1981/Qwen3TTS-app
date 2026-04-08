"""Voice clone tab with text and audio reference support"""

from datetime import datetime

from PySide6 import QtCore
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
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
from ..core.history import HistoryEntry


class _CloneWorker(QtCore.QObject):
    """Background worker for voice cloning."""

    finished = QtCore.Signal(bytes)
    error = QtCore.Signal(str)

    def __init__(self, api_client, text, config, ref_text=None, ref_audio_data=None):
        super().__init__()
        self._api_client = api_client
        self._text = text
        self._config = config
        self._ref_text = ref_text
        self._ref_audio_data = ref_audio_data

    def run(self):
        try:
            if self._ref_text is not None:
                result = self._api_client.clone_from_text(
                    self._text, self._ref_text, self._config
                )
            else:
                import io

                result = self._api_client.clone_from_audio(
                    self._text, io.BytesIO(self._ref_audio_data), self._config
                )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CloneTab(QWidget):
    def __init__(self, api_client, history_manager):
        super().__init__()
        self.api_client = api_client
        self.history_manager = history_manager
        self.audio_player = AudioPlayer()
        self.current_audio: bytes | None = None
        self.ref_audio_path: str | None = None
        self._thread: QtCore.QThread | None = None
        self._pending_info: dict = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("克隆模式："))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["文字參考", "音檔參考"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        input_group = QGroupBox("要合成的文字")
        input_layout = QVBoxLayout(input_group)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("請輸入要合成的文字...")
        self.text_input.setMinimumHeight(100)
        input_layout.addWidget(self.text_input)
        layout.addWidget(input_group)

        self.ref_group = QGroupBox("參考來源")
        ref_layout = QVBoxLayout(self.ref_group)

        self.ref_text_widget = QWidget()
        ref_text_layout = QVBoxLayout(self.ref_text_widget)
        ref_text_layout.addWidget(QLabel("參考文字（將用相同音色朗讀）："))
        self.ref_text_input = QTextEdit()
        self.ref_text_input.setPlaceholderText("請輸入參考文字...")
        self.ref_text_input.setMinimumHeight(80)
        ref_text_layout.addWidget(self.ref_text_input)
        ref_layout.addWidget(self.ref_text_widget)

        self.ref_audio_widget = QWidget()
        ref_audio_layout = QVBoxLayout(self.ref_audio_widget)
        ref_audio_layout.addWidget(QLabel("參考音檔（將克隆該音色）："))
        audio_select_layout = QHBoxLayout()
        self.ref_audio_label = QLabel("未選擇檔案")
        self.ref_audio_btn = QPushButton("選擇音檔")
        self.ref_audio_btn.clicked.connect(self._on_select_audio)
        audio_select_layout.addWidget(self.ref_audio_btn)
        audio_select_layout.addWidget(self.ref_audio_label)
        audio_select_layout.addStretch()
        ref_audio_layout.addLayout(audio_select_layout)
        ref_audio_layout.addWidget(QLabel("支援格式：WAV, MP3（建議時長 5-30 秒）"))
        self.ref_audio_widget.setVisible(False)
        ref_layout.addWidget(self.ref_audio_widget)

        layout.addWidget(self.ref_group)

        params_group = QGroupBox("合成參數")
        params_layout = QHBoxLayout(params_group)

        speed_layout = QVBoxLayout()
        speed_layout.addWidget(QLabel("語速"))
        self.speed_slider = QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_label = QLabel("1.0x")
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v / 100:.1f}x")
        )
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        params_layout.addLayout(speed_layout)

        pitch_layout = QVBoxLayout()
        pitch_layout.addWidget(QLabel("音調"))
        self.pitch_slider = QSlider(QtCore.Qt.Horizontal)
        self.pitch_slider.setRange(50, 200)
        self.pitch_slider.setValue(100)
        self.pitch_label = QLabel("1.0x")
        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_label.setText(f"{v / 100:.1f}x")
        )
        pitch_layout.addWidget(self.pitch_slider)
        pitch_layout.addWidget(self.pitch_label)
        params_layout.addLayout(pitch_layout)

        volume_layout = QVBoxLayout()
        volume_layout.addWidget(QLabel("音量"))
        self.volume_slider = QSlider(QtCore.Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_label = QLabel("1.0")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v / 100:.1f}")
        )
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)
        params_layout.addLayout(volume_layout)

        layout.addWidget(params_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        self.clone_btn = QPushButton("克隆語音")
        self.clone_btn.clicked.connect(self._on_clone)
        button_layout.addWidget(self.clone_btn)

        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self._on_play)
        self.play_btn.setEnabled(False)
        button_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton("匯出")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)

    def _on_mode_changed(self, index: int):
        if index == 0:
            self.ref_text_widget.setVisible(True)
            self.ref_audio_widget.setVisible(False)
        else:
            self.ref_text_widget.setVisible(False)
            self.ref_audio_widget.setVisible(True)

    def _on_select_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇參考音檔", "", "音訊檔案 (*.wav *.mp3);;所有檔案 (*.*)"
        )
        if path:
            self.ref_audio_path = path
            filename = path.split("/")[-1].split("\\")[-1]
            self.ref_audio_label.setText(filename)

    def _on_clone(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "請輸入要合成的文字")
            return

        if self._thread and self._thread.isRunning():
            return

        mode = self.mode_combo.currentIndex()
        config = self._get_tts_config()

        ref_text = None
        ref_audio_data = None
        ref_audio_name = None

        if mode == 0:
            ref_text = self.ref_text_input.toPlainText().strip()
            if not ref_text:
                QMessageBox.warning(self, "警告", "請輸入參考文字")
                return
        else:
            if not self.ref_audio_path:
                QMessageBox.warning(self, "警告", "請選擇參考音檔")
                return
            try:
                with open(self.ref_audio_path, "rb") as f:
                    ref_audio_data = f.read()
            except OSError as e:
                QMessageBox.critical(self, "錯誤", f"無法讀取音檔：{e}")
                return
            ref_audio_name = self.ref_audio_label.text()

        self._pending_info = {
            "text": text,
            "mode": mode,
            "config": config,
            "ref_text": ref_text,
            "ref_audio_name": ref_audio_name,
        }

        self.clone_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self._thread = QtCore.QThread()
        self._worker = _CloneWorker(
            self.api_client, text, config, ref_text=ref_text, ref_audio_data=ref_audio_data
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_clone_done)
        self._worker.error.connect(self._on_clone_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_clone_done(self, audio_data: bytes):
        self.current_audio = audio_data
        info = self._pending_info
        mode = info["mode"]
        config = info["config"]

        entry = HistoryEntry(
            id=self.history_manager.generate_id(),
            timestamp=datetime.now().isoformat(),
            operation=f"clone_{'text' if mode == 0 else 'audio'}",
            text=info["text"],
            ref_text=info["ref_text"],
            ref_audio_name=info["ref_audio_name"],
            config={
                "speed": config.speed,
                "pitch": config.pitch,
                "volume": config.volume,
            },
            audio_duration=AudioExporter.get_info(audio_data)["duration"],
        )
        self.history_manager.add(entry)

        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.clone_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _on_clone_error(self, error: str):
        QMessageBox.critical(self, "錯誤", f"克隆失敗：{error}")
        self.clone_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _get_tts_config(self):
        from ..api.qwen3_client import TTSConfig

        return TTSConfig(
            speed=self.speed_slider.value() / 100,
            pitch=self.pitch_slider.value() / 100,
            volume=self.volume_slider.value() / 100,
        )

    def _on_play(self):
        if self.current_audio:
            if self.audio_player.is_playing():
                self.audio_player.pause()
                self.play_btn.setText("繼續")
            else:
                self.audio_player.play(self.current_audio)
                self.play_btn.setText("暫停")

    def _on_stop(self):
        self.audio_player.stop()
        self.play_btn.setText("播放")

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
                QMessageBox.information(self, "成功", f"已匯出至：{path}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"匯出失敗：{str(e)}")
