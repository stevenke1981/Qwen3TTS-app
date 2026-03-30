"""Settings tab for configuration management"""

from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QCheckBox,
    QComboBox,
)

from ..core.config import Config
from .theme import make_secondary_button


class SettingsTab(QWidget):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        qwen3_group = QGroupBox("Qwen3-TTS API 設定")
        qwen3_layout = QFormLayout(qwen3_group)

        self.url_input = QLineEdit(self.config.api.qwen3_base_url)
        qwen3_layout.addRow("API URL：", self.url_input)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.setValue(self.config.api.qwen3_timeout)
        qwen3_layout.addRow("超時時間：", self.timeout_spin)

        self.verify_ssl_cb = QCheckBox("驗證 SSL 憑證")
        self.verify_ssl_cb.setChecked(self.config.api.verify_ssl)
        qwen3_layout.addRow("", self.verify_ssl_cb)

        layout.addWidget(qwen3_group)

        ollama_group = QGroupBox("Ollama API 設定")
        ollama_layout = QFormLayout(ollama_group)

        self.ollama_url_input = QLineEdit(self.config.ollama.base_url)
        ollama_layout.addRow("API URL：", self.ollama_url_input)

        self.model_input = QLineEdit(self.config.ollama.default_model)
        ollama_layout.addRow("預設模型：", self.model_input)

        layout.addWidget(ollama_group)

        audio_group = QGroupBox("音訊設定")
        audio_layout = QFormLayout(audio_group)

        self.sample_rate_label = QLabel(f"{self.config.audio.sample_rate} Hz")
        audio_layout.addRow("取樣率：", self.sample_rate_label)

        self.format_label = QLabel(self.config.audio.format.upper())
        audio_layout.addRow("格式：", self.format_label)

        layout.addWidget(audio_group)

        ui_group = QGroupBox("UI 設定")
        ui_layout = QFormLayout(ui_group)

        width_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(600, 1920)
        self.width_spin.setValue(self.config.ui.window_size[0])
        self.height_spin = QSpinBox()
        self.height_spin.setRange(400, 1080)
        self.height_spin.setValue(self.config.ui.window_size[1])
        width_layout.addWidget(self.width_spin)
        width_layout.addWidget(QLabel("×"))
        width_layout.addWidget(self.height_spin)
        ui_layout.addRow("視窗大小：", width_layout)

        layout.addWidget(ui_group)

        layout.addStretch()

        button_layout = QHBoxLayout()
        self.test_qwen3_btn = QPushButton("🔌  測試 Qwen3 連線")
        self.test_qwen3_btn.clicked.connect(self._on_test_qwen3)
        self.test_qwen3_btn.setToolTip("測試 Qwen3-TTS API 連線狀態")
        make_secondary_button(self.test_qwen3_btn)
        button_layout.addWidget(self.test_qwen3_btn)

        self.test_ollama_btn = QPushButton("🔌  測試 Ollama 連線")
        self.test_ollama_btn.clicked.connect(self._on_test_ollama)
        self.test_ollama_btn.setToolTip("測試 Ollama 連線狀態並列出可用模型")
        make_secondary_button(self.test_ollama_btn)
        button_layout.addWidget(self.test_ollama_btn)

        layout.addLayout(button_layout)

        save_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾  儲存設定")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setToolTip("將目前設定儲存到 config.yaml")
        save_layout.addStretch()
        save_layout.addWidget(self.save_btn)

        layout.addLayout(save_layout)

    def _on_test_qwen3(self):
        from ..api.qwen3_client import Qwen3Client

        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "請輸入 API URL")
            return

        client = Qwen3Client(url)
        if client.health_check():
            QMessageBox.information(self, "成功", "Qwen3-TTS API 服務正常運行！")
        else:
            QMessageBox.warning(
                self, "連線失敗", "無法連接到 API 服務，請確認 URL 是否正確"
            )

    def _on_test_ollama(self):
        from ..api.ollama_client import OllamaClient

        url = self.ollama_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "請輸入 Ollama URL")
            return

        client = OllamaClient(url)
        if client.health_check():
            models = client.list_models()
            model_info = f"Ollama 服務正常運行！\n\n可用模型：\n" + "\n".join(
                f"  • {m}" for m in models[:10]
            )
            if len(models) > 10:
                model_info += f"\n  ... 及其他 {len(models) - 10} 個模型"
            QMessageBox.information(self, "成功", model_info)
        else:
            QMessageBox.warning(self, "連線失敗", "無法連接到 Ollama 服務")

    def _on_save(self):
        self.config.api.qwen3_base_url = self.url_input.text().strip()
        self.config.api.qwen3_timeout = self.timeout_spin.value()
        self.config.api.verify_ssl = self.verify_ssl_cb.isChecked()
        self.config.ollama.base_url = self.ollama_url_input.text().strip()
        self.config.ollama.default_model = self.model_input.text().strip()
        self.config.ui.window_size = (
            self.width_spin.value(),
            self.height_spin.value(),
        )

        try:
            config_path = self._get_config_path()
            self.config.to_yaml(config_path)
            QMessageBox.information(self, "成功", "設定已儲存！")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存失敗：{str(e)}")

    def _get_config_path(self):
        from pathlib import Path

        return Path(__file__).parent.parent.parent / "config.yaml"
