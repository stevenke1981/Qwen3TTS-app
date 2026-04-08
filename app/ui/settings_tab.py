"""Settings tab — tabbed layout with TTS / LLM / ASR / Audio / About sub-pages."""

import platform
import sys

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.config import Config
from .theme import (
    COLOR_ERROR,
    COLOR_SUCCESS,
    make_secondary_button,
)


class SettingsTab(QWidget):
    def __init__(self, config: Config, asr_client=None):
        super().__init__()
        self.config = config
        self._asr_client = asr_client
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._build_tts_page(), "🎙  TTS 設定")
        self._tabs.addTab(self._build_llm_page(), "🤖  LLM 設定")
        self._tabs.addTab(self._build_asr_page(), "🎧  ASR 設定")
        self._tabs.addTab(self._build_audio_ui_page(), "🔊  音訊 / UI")
        self._tabs.addTab(self._build_about_page(), "ℹ  系統資訊")

        # ── Bottom button bar ──
        btn_layout = QHBoxLayout()
        self.export_config_btn = QPushButton("📤  匯出設定")
        self.export_config_btn.clicked.connect(self._on_export_config)
        self.export_config_btn.setToolTip("匯出目前設定到 YAML 檔案")
        make_secondary_button(self.export_config_btn)
        btn_layout.addWidget(self.export_config_btn)

        self.import_config_btn = QPushButton("📥  匯入設定")
        self.import_config_btn.clicked.connect(self._on_import_config)
        self.import_config_btn.setToolTip("從 YAML 檔案匯入設定")
        make_secondary_button(self.import_config_btn)
        btn_layout.addWidget(self.import_config_btn)

        btn_layout.addStretch()

        self.save_btn = QPushButton("💾  儲存設定")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setToolTip("將目前設定儲存到 config.yaml")
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    # ═══════════════════════════════════════════════════════════════════════════
    # TTS page
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_tts_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # ── Local TTS Server ──
        srv_group = QGroupBox("本地 TTS 伺服器")
        srv_layout = QFormLayout(srv_group)

        self.tts_auto_start_cb = QCheckBox("啟動時自動開啟 TTS 伺服器")
        self.tts_auto_start_cb.setChecked(self.config.tts_server.auto_start)
        srv_layout.addRow("", self.tts_auto_start_cb)

        self.tts_model_input = QLineEdit(self.config.tts_server.model_id)
        srv_layout.addRow("模型 ID：", self.tts_model_input)

        self.tts_device_combo = QComboBox()
        self.tts_device_combo.addItems(["cpu", "cuda", "cuda:0", "cuda:1"])
        idx = self.tts_device_combo.findText(self.config.tts_server.device)
        if idx >= 0:
            self.tts_device_combo.setCurrentIndex(idx)
        srv_layout.addRow("裝置：", self.tts_device_combo)

        self.tts_port_spin = QSpinBox()
        self.tts_port_spin.setRange(1024, 65535)
        self.tts_port_spin.setValue(self.config.tts_server.port)
        srv_layout.addRow("連接埠：", self.tts_port_spin)

        layout.addWidget(srv_group)

        # ── API settings ──
        api_group = QGroupBox("TTS API 設定（遠端模式）")
        api_layout = QFormLayout(api_group)

        self.url_input = QLineEdit(self.config.api.qwen3_base_url)
        api_layout.addRow("API URL：", self.url_input)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.setValue(self.config.api.qwen3_timeout)
        api_layout.addRow("超時時間：", self.timeout_spin)

        self.verify_ssl_cb = QCheckBox("驗證 SSL 憑證")
        self.verify_ssl_cb.setChecked(self.config.api.verify_ssl)
        api_layout.addRow("", self.verify_ssl_cb)

        layout.addWidget(api_group)

        # Test button
        test_row = QHBoxLayout()
        self.test_qwen3_btn = QPushButton("🔌  測試 TTS 連線")
        self.test_qwen3_btn.clicked.connect(self._on_test_qwen3)
        make_secondary_button(self.test_qwen3_btn)
        test_row.addWidget(self.test_qwen3_btn)
        test_row.addStretch()
        layout.addLayout(test_row)
        layout.addStretch()
        return page

    # ═══════════════════════════════════════════════════════════════════════════
    # LLM page
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_llm_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # ── Local LLM Server ──
        srv_group = QGroupBox("本地 LLM 伺服器")
        srv_layout = QFormLayout(srv_group)

        self.llm_auto_start_cb = QCheckBox("啟動時自動開啟 LLM 伺服器")
        self.llm_auto_start_cb.setChecked(self.config.llm_server.auto_start)
        srv_layout.addRow("", self.llm_auto_start_cb)

        self.llm_srv_model_input = QLineEdit(self.config.llm_server.model_id)
        srv_layout.addRow("模型 ID：", self.llm_srv_model_input)

        self.llm_device_combo = QComboBox()
        self.llm_device_combo.addItems(["cpu", "cuda", "cuda:0", "cuda:1"])
        idx = self.llm_device_combo.findText(self.config.llm_server.device)
        if idx >= 0:
            self.llm_device_combo.setCurrentIndex(idx)
        srv_layout.addRow("裝置：", self.llm_device_combo)

        self.llm_port_spin = QSpinBox()
        self.llm_port_spin.setRange(1024, 65535)
        self.llm_port_spin.setValue(self.config.llm_server.port)
        srv_layout.addRow("連接埠：", self.llm_port_spin)

        layout.addWidget(srv_group)

        # ── API / provider settings ──
        api_group = QGroupBox("LLM 潤稿翻譯 設定")
        api_layout = QFormLayout(api_group)

        self.llm_provider_combo = QComboBox()
        self.llm_provider_combo.addItems(["fastapi", "ollama", "openai"])
        idx = self.llm_provider_combo.findText(self.config.llm.provider)
        if idx >= 0:
            self.llm_provider_combo.setCurrentIndex(idx)
        api_layout.addRow("模式：", self.llm_provider_combo)

        self.llm_url_input = QLineEdit(self.config.llm.base_url)
        api_layout.addRow("Base URL：", self.llm_url_input)

        self.llm_api_key_input = QLineEdit(self.config.llm.api_key)
        self.llm_api_key_input.setPlaceholderText("可留空（本地）")
        self.llm_api_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key：", self.llm_api_key_input)

        self.llm_model_input = QLineEdit(self.config.llm.model)
        api_layout.addRow("模型：", self.llm_model_input)

        layout.addWidget(api_group)

        test_row = QHBoxLayout()
        self.test_llm_btn = QPushButton("🔌  測試 LLM 連線")
        self.test_llm_btn.clicked.connect(self._on_test_llm)
        make_secondary_button(self.test_llm_btn)
        test_row.addWidget(self.test_llm_btn)
        test_row.addStretch()
        layout.addLayout(test_row)
        layout.addStretch()
        return page

    # ═══════════════════════════════════════════════════════════════════════════
    # ASR page
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_asr_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Qwen3 ASR 設定")
        form = QFormLayout(group)

        self.asr_mode_combo = QComboBox()
        self.asr_mode_combo.addItems(["local（本地 venv-asr）", "api（遠端 API）"])
        self.asr_mode_combo.setCurrentIndex(1 if self.config.asr.mode == "api" else 0)
        self.asr_mode_combo.currentIndexChanged.connect(self._on_asr_mode_changed)
        form.addRow("模式：", self.asr_mode_combo)

        self.asr_api_url_input = QLineEdit(self.config.asr.api_url)
        self.asr_api_url_input.setPlaceholderText("例：http://192.168.1.100:8002")
        form.addRow("API URL：", self.asr_api_url_input)

        self.asr_api_key_input = QLineEdit(self.config.asr.api_key)
        self.asr_api_key_input.setPlaceholderText("可留空")
        self.asr_api_key_input.setEchoMode(QLineEdit.Password)
        form.addRow("API Key：", self.asr_api_key_input)

        layout.addWidget(group)

        test_row = QHBoxLayout()
        self.test_asr_btn = QPushButton("🔌  測試 ASR 連線")
        self.test_asr_btn.clicked.connect(self._on_test_asr)
        make_secondary_button(self.test_asr_btn)
        test_row.addWidget(self.test_asr_btn)
        test_row.addStretch()
        layout.addLayout(test_row)
        layout.addStretch()

        self._on_asr_mode_changed()
        return page

    # ═══════════════════════════════════════════════════════════════════════════
    # Audio / UI page
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_audio_ui_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

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

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        idx = self.theme_combo.findText(self.config.ui.theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        ui_layout.addRow("主題：", self.theme_combo)

        layout.addWidget(ui_group)
        layout.addStretch()
        return page

    # ═══════════════════════════════════════════════════════════════════════════
    # About / System info page
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        from ..core.model_manager import get_gpu_info, get_missing_models

        info_group = QGroupBox("系統資訊")
        form = QFormLayout(info_group)

        form.addRow("應用版本：", QLabel("0.4.0"))
        form.addRow("Python：", QLabel(f"{sys.version.split()[0]}"))
        form.addRow("平台：", QLabel(f"{platform.system()} {platform.release()}"))
        form.addRow("GPU：", QLabel(get_gpu_info()))

        missing = get_missing_models()
        if missing:
            names = ", ".join(m.name for m in missing)
            model_lbl = QLabel(f"缺少：{names}")
            model_lbl.setStyleSheet(f"color: {COLOR_ERROR};")
        else:
            model_lbl = QLabel("所有默認模型已安裝 ✓")
            model_lbl.setStyleSheet(f"color: {COLOR_SUCCESS};")
        form.addRow("模型狀態：", model_lbl)
        layout.addWidget(info_group)

        # ── Health dashboard ──
        health_group = QGroupBox("服務狀態")
        health_layout = QFormLayout(health_group)

        self._tts_status = QLabel("⏳ 檢測中…")
        health_layout.addRow("TTS 伺服器：", self._tts_status)
        self._llm_status = QLabel("⏳ 檢測中…")
        health_layout.addRow("LLM 伺服器：", self._llm_status)

        layout.addWidget(health_group)

        # Refresh status
        refresh_row = QHBoxLayout()
        self.refresh_status_btn = QPushButton("🔄  重新檢測")
        self.refresh_status_btn.clicked.connect(self._refresh_health)
        make_secondary_button(self.refresh_status_btn)
        refresh_row.addWidget(self.refresh_status_btn)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        layout.addStretch()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self._refresh_health)

        return page

    # ═══════════════════════════════════════════════════════════════════════════
    # Event handlers
    # ═══════════════════════════════════════════════════════════════════════════
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

    def _refresh_health(self):
        """Check TTS and LLM server health (quick sync probe)."""
        import requests as _req
        for label, port in [
            (self._tts_status, self.config.tts_server.port),
            (self._llm_status, self.config.llm_server.port),
        ]:
            try:
                resp = _req.get(f"http://localhost:{port}/health", timeout=2)
                if resp.status_code == 200:
                    label.setText("✅ 運行中")
                    label.setStyleSheet(f"color: {COLOR_SUCCESS};")
                else:
                    label.setText(f"⚠️ 回應異常 ({resp.status_code})")
                    label.setStyleSheet(f"color: {COLOR_ERROR};")
            except Exception:
                label.setText("❌ 未運行")
                label.setStyleSheet(f"color: {COLOR_ERROR};")

    def _on_save(self):
        # TTS server
        self.config.tts_server.auto_start = self.tts_auto_start_cb.isChecked()
        self.config.tts_server.model_id = self.tts_model_input.text().strip()
        self.config.tts_server.device = self.tts_device_combo.currentText()
        self.config.tts_server.port = self.tts_port_spin.value()
        # TTS API
        self.config.api.qwen3_base_url = self.url_input.text().strip()
        self.config.api.qwen3_timeout = self.timeout_spin.value()
        self.config.api.verify_ssl = self.verify_ssl_cb.isChecked()
        # LLM server
        self.config.llm_server.auto_start = self.llm_auto_start_cb.isChecked()
        self.config.llm_server.model_id = self.llm_srv_model_input.text().strip()
        self.config.llm_server.device = self.llm_device_combo.currentText()
        self.config.llm_server.port = self.llm_port_spin.value()
        # LLM API
        self.config.llm.provider = self.llm_provider_combo.currentText()
        self.config.llm.base_url = self.llm_url_input.text().strip()
        self.config.llm.api_key  = self.llm_api_key_input.text().strip()
        self.config.llm.model    = self.llm_model_input.text().strip()
        # ASR
        asr_mode = "api" if self.asr_mode_combo.currentIndex() == 1 else "local"
        self.config.asr.mode    = asr_mode
        self.config.asr.api_url = self.asr_api_url_input.text().strip()
        self.config.asr.api_key = self.asr_api_key_input.text().strip()
        if self._asr_client is not None:
            self._asr_client.mode    = asr_mode
            self._asr_client.api_url = self.config.asr.api_url
            self._asr_client.api_key = self.config.asr.api_key
        # UI
        self.config.ui.window_size = (self.width_spin.value(), self.height_spin.value())
        self.config.ui.theme = self.theme_combo.currentText()

        try:
            config_path = self._get_config_path()
            self.config.to_yaml(config_path)
            QMessageBox.information(self, "成功", "設定已儲存！")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存失敗：{str(e)}")

    def _get_config_path(self):
        from pathlib import Path
        return Path(__file__).parent.parent.parent / "config.yaml"

    def _on_export_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "匯出設定", "config_backup.yaml", "YAML (*.yaml *.yml);;所有檔案 (*.*)"
        )
        if not path:
            return
        try:
            self.config.to_yaml(path)
            QMessageBox.information(self, "成功", f"設定已匯出至：{path}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯出失敗：{e}")

    def _on_import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "匯入設定", "", "YAML (*.yaml *.yml);;所有檔案 (*.*)"
        )
        if not path:
            return
        try:
            from ..core.config import Config

            new_cfg = Config.from_yaml(path)
            self.config.api = new_cfg.api
            self.config.llm = new_cfg.llm
            self.config.asr = new_cfg.asr
            self.config.audio = new_cfg.audio
            self.config.ui = new_cfg.ui
            self.config.tts_server = new_cfg.tts_server
            self.config.llm_server = new_cfg.llm_server
            # Refresh widgets
            self.url_input.setText(self.config.api.qwen3_base_url)
            self.timeout_spin.setValue(self.config.api.qwen3_timeout)
            self.verify_ssl_cb.setChecked(self.config.api.verify_ssl)
            idx = self.llm_provider_combo.findText(self.config.llm.provider)
            if idx >= 0:
                self.llm_provider_combo.setCurrentIndex(idx)
            self.llm_url_input.setText(self.config.llm.base_url)
            self.llm_api_key_input.setText(self.config.llm.api_key)
            self.llm_model_input.setText(self.config.llm.model)
            self.width_spin.setValue(self.config.ui.window_size[0])
            self.height_spin.setValue(self.config.ui.window_size[1])
            QMessageBox.information(self, "成功", f"已匯入設定：{path}\n請按「儲存設定」以保留。")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯入失敗：{e}")
