"""Settings tab for configuration management"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.config import Config
from .theme import make_secondary_button


class SettingsTab(QWidget):
    def __init__(self, config: Config, asr_client=None):
        super().__init__()
        self.config = config
        self._asr_client = asr_client
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

        # ── LLM (潤稿/翻譯) 設定 ───────────────────────────────────────────────
        llm_group = QGroupBox("LLM 潤稿翻譯 設定")
        llm_layout = QFormLayout(llm_group)

        self.llm_provider_combo = QComboBox()
        self.llm_provider_combo.addItems(["ollama", "openai", "fastapi"])
        idx = self.llm_provider_combo.findText(self.config.llm.provider)
        if idx >= 0:
            self.llm_provider_combo.setCurrentIndex(idx)
        llm_layout.addRow("模式：", self.llm_provider_combo)

        self.llm_url_input = QLineEdit(self.config.llm.base_url)
        llm_layout.addRow("Base URL：", self.llm_url_input)

        self.llm_api_key_input = QLineEdit(self.config.llm.api_key)
        self.llm_api_key_input.setPlaceholderText("可留空（Ollama）")
        self.llm_api_key_input.setEchoMode(QLineEdit.Password)
        llm_layout.addRow("API Key：", self.llm_api_key_input)

        self.llm_model_input = QLineEdit(self.config.llm.model)
        llm_layout.addRow("模型：", self.llm_model_input)

        layout.addWidget(llm_group)

        # ── ASR 設定 ───────────────────────────────────────────────────────────
        asr_group = QGroupBox("Qwen3 ASR 設定")
        asr_layout = QFormLayout(asr_group)

        self.asr_mode_combo = QComboBox()
        self.asr_mode_combo.addItems(["local（本地 venv-asr）", "api（遠端 API）"])
        self.asr_mode_combo.setCurrentIndex(1 if self.config.asr.mode == "api" else 0)
        self.asr_mode_combo.currentIndexChanged.connect(self._on_asr_mode_changed)
        asr_layout.addRow("模式：", self.asr_mode_combo)

        self.asr_api_url_input = QLineEdit(self.config.asr.api_url)
        self.asr_api_url_input.setPlaceholderText("例：http://192.168.1.100:8002")
        asr_layout.addRow("API URL：", self.asr_api_url_input)

        self.asr_api_key_input = QLineEdit(self.config.asr.api_key)
        self.asr_api_key_input.setPlaceholderText("可留空")
        self.asr_api_key_input.setEchoMode(QLineEdit.Password)
        asr_layout.addRow("API Key：", self.asr_api_key_input)

        layout.addWidget(asr_group)

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

        self.test_llm_btn = QPushButton("🔌  測試 LLM 連線")
        self.test_llm_btn.clicked.connect(self._on_test_llm)
        self.test_llm_btn.setToolTip("測試 LLM 連線狀態並列出可用模型")
        make_secondary_button(self.test_llm_btn)
        button_layout.addWidget(self.test_llm_btn)

        self.test_asr_btn = QPushButton("🔌  測試 ASR API")
        self.test_asr_btn.clicked.connect(self._on_test_asr)
        self.test_asr_btn.setToolTip("測試遠端 ASR API 連線狀態")
        make_secondary_button(self.test_asr_btn)
        button_layout.addWidget(self.test_asr_btn)

        layout.addLayout(button_layout)

        save_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾  儲存設定")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setToolTip("將目前設定儲存到 config.yaml")
        save_layout.addStretch()
        save_layout.addWidget(self.save_btn)

        layout.addLayout(save_layout)

        self._on_asr_mode_changed()  # Apply initial visibility for ASR fields

    def _on_asr_mode_changed(self):
        api_mode = self.asr_mode_combo.currentIndex() == 1
        self.asr_api_url_input.setEnabled(api_mode)
        self.asr_api_key_input.setEnabled(api_mode)
        self.test_asr_btn.setEnabled(api_mode)

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

    def _on_test_asr(self):
        url = self.asr_api_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "請輸入 ASR API URL")
            return
        import requests as _req
        api_key = self.asr_api_key_input.text().strip()
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            resp = _req.get(f"{url.rstrip('/')}/health", headers=headers, timeout=5)
            if resp.status_code == 200:
                QMessageBox.information(self, "成功", f"ASR API 服務正常！\n{url}")
            else:
                QMessageBox.warning(self, "連線失敗", f"回應狀態碼：{resp.status_code}")
        except Exception as exc:
            QMessageBox.warning(self, "連線失敗", f"無法連接到 ASR API：{exc}")

    def _on_test_llm(self):
        from ..api.llm_client import LLMClient

        url = self.llm_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "請輸入 LLM Base URL")
            return

        provider = self.llm_provider_combo.currentText()
        api_key  = self.llm_api_key_input.text().strip()
        model    = self.llm_model_input.text().strip()
        client = LLMClient(provider=provider, base_url=url, api_key=api_key, model=model)
        if client.health_check():
            models = client.list_models()
            info = f"LLM 服務正常運行！\n提供商：{provider}\n\n可用模型：\n" + "\n".join(
                f"  • {m}" for m in models[:10]
            )
            if len(models) > 10:
                info += f"\n  ... 及其他 {len(models) - 10} 個模型"
            QMessageBox.information(self, "成功", info)
        else:
            QMessageBox.warning(self, "連線失敗", f"無法連接到 LLM 服務（{provider} @ {url}）")

    def _on_save(self):
        self.config.api.qwen3_base_url = self.url_input.text().strip()
        self.config.api.qwen3_timeout = self.timeout_spin.value()
        self.config.api.verify_ssl = self.verify_ssl_cb.isChecked()
        self.config.llm.provider  = self.llm_provider_combo.currentText()
        self.config.llm.base_url  = self.llm_url_input.text().strip()
        self.config.llm.api_key   = self.llm_api_key_input.text().strip()
        self.config.llm.model     = self.llm_model_input.text().strip()
        asr_mode = "api" if self.asr_mode_combo.currentIndex() == 1 else "local"
        self.config.asr.mode    = asr_mode
        self.config.asr.api_url = self.asr_api_url_input.text().strip()
        self.config.asr.api_key = self.asr_api_key_input.text().strip()
        # Sync live asr_client if available
        if self._asr_client is not None:
            self._asr_client.mode    = asr_mode
            self._asr_client.api_url = self.config.asr.api_url
            self._asr_client.api_key = self.config.asr.api_key
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
