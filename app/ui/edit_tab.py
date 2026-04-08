"""Edit & Translate tab with multi-provider LLM integration"""

from datetime import datetime

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.chinese_converter import ChineseConverter
from ..core.history import HistoryEntry


class _EditWorker(QtCore.QObject):
    """Background worker for LLM text processing."""

    finished = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, llm_client, text, mode, instruction=""):
        super().__init__()
        self._client = llm_client
        self._text = text
        self._mode = mode
        self._instruction = instruction

    def run(self):
        try:
            if self._mode == 0:
                result = self._client.polish(self._text)
            elif self._mode == 3:
                result = self._client.translate(self._text, "en", "zh")
            elif self._mode == 4:
                result = self._client.translate(self._text, "zh", "en")
            elif self._mode == 5:
                result = self._client.translate(self._text, "ja", "zh")
            elif self._mode == 6:
                result = self._client.custom_process(self._text, self._instruction)
            else:
                result = self._text
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class EditTab(QWidget):
    text_sent = QtCore.Signal(str)
    text_sent_to_clone = QtCore.Signal(str)

    def __init__(self, llm_client, qwen3_client, history_manager):
        super().__init__()
        self.llm_client = llm_client
        self.qwen3_client = qwen3_client
        self.history_manager = history_manager
        self._thread: QtCore.QThread | None = None
        self._pending_text: str = ""
        self._pending_mode: int = 0

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        input_group = QGroupBox("原文輸入")
        input_layout = QVBoxLayout(input_group)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("請輸入要處理的文字...")
        self.input_text.setMinimumHeight(150)
        input_layout.addWidget(self.input_text)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("處理模式："))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [
                "潤稿（保持原語言）",
                "中文簡→繁",
                "中文繁→簡",
                "英→中翻譯",
                "中→英翻譯",
                "日→中翻譯",
                "自訂指令",
            ]
        )
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        input_layout.addLayout(mode_layout)

        self.custom_prompt_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_prompt_widget)
        custom_layout.addWidget(QLabel("自訂指令："))
        self.custom_prompt_input = QLineEdit()
        self.custom_prompt_input.setPlaceholderText("例：請將以下文字改為更專業的口吻")
        custom_layout.addWidget(self.custom_prompt_input)
        self.custom_prompt_widget.setVisible(False)
        input_layout.addWidget(self.custom_prompt_widget)

        left_layout.addWidget(input_group)

        button_layout = QHBoxLayout()
        self.process_btn = QPushButton("處理")
        self.process_btn.clicked.connect(self._on_process)
        button_layout.addWidget(self.process_btn)

        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self._on_clear)
        button_layout.addWidget(self.clear_btn)

        left_layout.addLayout(button_layout)

        output_group = QGroupBox("處理結果")
        output_layout = QVBoxLayout(output_group)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(150)
        output_layout.addWidget(self.output_text)

        convert_layout = QHBoxLayout()
        self.s2t_btn = QPushButton("簡→繁")
        self.s2t_btn.clicked.connect(lambda: self._on_convert("s2t"))
        convert_layout.addWidget(self.s2t_btn)

        self.t2s_btn = QPushButton("繁→簡")
        self.t2s_btn.clicked.connect(lambda: self._on_convert("t2s"))
        convert_layout.addWidget(self.t2s_btn)

        self.copy_btn = QPushButton("複製")
        self.copy_btn.clicked.connect(self._on_copy)
        convert_layout.addWidget(self.copy_btn)

        output_layout.addLayout(convert_layout)
        left_layout.addWidget(output_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        main_layout.addWidget(left_panel, stretch=2)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        info_group = QGroupBox("快速操作")
        info_layout = QVBoxLayout(info_group)

        send_to_tts_btn = QPushButton("送往文字合成")
        send_to_tts_btn.clicked.connect(self._on_send_to_tts)
        info_layout.addWidget(send_to_tts_btn)

        send_to_clone_btn = QPushButton("送往語音克隆")
        send_to_clone_btn.clicked.connect(self._on_send_to_clone)
        info_layout.addWidget(send_to_clone_btn)

        info_layout.addStretch()
        right_layout.addWidget(info_group)

        model_group = QGroupBox("模型資訊")
        model_layout = QVBoxLayout(model_group)

        self.model_label = QLabel(f"模型：{self.llm_client.default_model}")
        model_layout.addWidget(self.model_label)

        self.test_llm_btn = QPushButton("測試 LLM 連線")
        self.test_llm_btn.clicked.connect(self._on_test_llm)
        model_layout.addWidget(self.test_llm_btn)

        right_layout.addWidget(model_group)
        right_layout.addStretch()

        main_layout.addWidget(right_panel, stretch=1)

    def _on_mode_changed(self, index: int):
        self.custom_prompt_widget.setVisible(index == 6)

    def _on_process(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "請輸入要處理的文字")
            return

        mode = self.mode_combo.currentIndex()

        # 本地轉換（繁簡互轉）不需要後台執行緒
        if mode == 1:
            try:
                result = ChineseConverter.s2t(text)
                self.output_text.setPlainText(result)
                self._save_history(text, mode)
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"轉換失敗：{str(e)}")
            return

        if mode == 2:
            try:
                result = ChineseConverter.t2s(text)
                self.output_text.setPlainText(result)
                self._save_history(text, mode)
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"轉換失敗：{str(e)}")
            return

        # Ollama 呼叫→ 後台執行緒
        if self._thread and self._thread.isRunning():
            return

        if mode == 6:
            instruction = self.custom_prompt_input.text().strip()
            if not instruction:
                QMessageBox.warning(self, "警告", "請輸入自訂指令")
                return
        else:
            instruction = ""

        self._pending_text = text
        self._pending_mode = mode
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self._thread = QtCore.QThread()
        self._worker = _EditWorker(self.llm_client, text, mode, instruction)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_process_done)
        self._worker.error.connect(self._on_process_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_process_done(self, result: str):
        self.output_text.setPlainText(result)
        self._save_history(self._pending_text, self._pending_mode)
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _on_process_error(self, error: str):
        QMessageBox.critical(self, "錯誤", f"處理失敗：{error}")
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _save_history(self, text: str, mode: int):
        entry = HistoryEntry(
            id=self.history_manager.generate_id(),
            timestamp=datetime.now().isoformat(),
            operation=f"edit_mode_{mode}",
            text=text,
            config={"mode": self.mode_combo.currentText()},
        )
        self.history_manager.add(entry)

    def _on_convert(self, direction: str):
        text = self.output_text.toPlainText().strip()
        if not text:
            return

        try:
            if direction == "s2t":
                result = ChineseConverter.s2t(text)
            else:
                result = ChineseConverter.t2s(text)
            self.output_text.setPlainText(result)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"轉換失敗：{str(e)}")

    def _on_copy(self):
        text = self.output_text.toPlainText()
        if text:
            QtWidgets.QApplication.clipboard().setText(text)

    def _on_clear(self):
        self.input_text.clear()
        self.output_text.clear()

    def _on_test_llm(self):
        if self.llm_client.health_check():
            QMessageBox.information(self, "成功", "LLM 服務正常運行！")
        else:
            QMessageBox.warning(self, "連線失敗", "無法連接到 LLM 服務")

    def _on_send_to_tts(self):
        text = self.output_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "沒有可發送的文字")
            return
        self.text_sent.emit(text)

    def _on_send_to_clone(self):
        text = self.output_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "沒有可發送的文字")
            return
        self.text_sent_to_clone.emit(text)


