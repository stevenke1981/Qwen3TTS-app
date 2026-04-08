"""Tests for v0.5.0 additions: ASRServerConfig, ErrorConsoleWidget, ServerManager.asr."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

# ── ASRServerConfig ────────────────────────────────────────────────────────────

class TestASRServerConfig:
    def test_defaults(self):
        from app.core.config import ASRServerConfig
        cfg = ASRServerConfig()
        assert cfg.model_id == "Qwen/Qwen3-ASR-0.6B"
        assert cfg.device == "cpu"
        assert cfg.port == 8002
        assert cfg.auto_start is True

    def test_custom_values(self):
        from app.core.config import ASRServerConfig
        cfg = ASRServerConfig(model_id="Qwen/Qwen3-ASR-1.7B", device="cuda", port=9002, auto_start=False)
        assert cfg.model_id == "Qwen/Qwen3-ASR-1.7B"
        assert cfg.device == "cuda"
        assert cfg.port == 9002
        assert cfg.auto_start is False


class TestConfigASRSection:
    def test_config_has_asr_server_field(self):
        from app.core.config import ASRServerConfig, Config
        cfg = Config()
        assert hasattr(cfg, "asr_server")
        assert isinstance(cfg.asr_server, ASRServerConfig)

    def test_from_dict_parses_asr_server(self):
        from app.core.config import Config
        data = {
            "asr_server": {
                "model_id": "Qwen/Qwen3-ASR-1.7B",
                "device": "cuda",
                "port": 9002,
                "auto_start": False,
            }
        }
        cfg = Config._from_dict(data)
        assert cfg.asr_server.model_id == "Qwen/Qwen3-ASR-1.7B"
        assert cfg.asr_server.device == "cuda"
        assert cfg.asr_server.port == 9002
        assert cfg.asr_server.auto_start is False

    def test_from_dict_uses_defaults_when_asr_section_missing(self):
        from app.core.config import Config
        cfg = Config._from_dict({})
        assert cfg.asr_server.port == 8002
        assert cfg.asr_server.auto_start is True

    def test_to_yaml_roundtrip_asr_server(self, tmp_path: Path):
        from app.core.config import Config
        cfg = Config()
        cfg.asr_server.model_id = "Qwen/Qwen3-ASR-1.7B"
        cfg.asr_server.port = 9002
        p = tmp_path / "cfg.yaml"
        cfg.to_yaml(p)
        loaded = Config.from_yaml(p)
        assert loaded.asr_server.model_id == "Qwen/Qwen3-ASR-1.7B"
        assert loaded.asr_server.port == 9002


# ── ServerManager — ASR server ─────────────────────────────────────────────────

class TestServerManagerASR:
    def test_has_asr_attribute(self):
        from app.core.server_manager import ServerManager
        sm = ServerManager()
        assert hasattr(sm, "asr")
        assert sm.asr is not None

    def test_asr_in_status(self):
        from app.core.server_manager import ServerManager
        sm = ServerManager()
        result = sm.status()
        assert "ASR Server" in result

    def test_asr_status_keys(self):
        from app.core.server_manager import ServerManager
        sm = ServerManager()
        info = sm.status()["ASR Server"]
        assert "running" in info
        assert "healthy" in info
        assert "venv_ready" in info

    def test_stop_all_safe_with_asr(self):
        from app.core.server_manager import ServerManager
        sm = ServerManager()
        sm.stop_all()   # must not raise


# ── ErrorConsoleHandler (headless, no QApplication needed) ─────────────────────

class TestErrorConsoleHandler:
    def test_handler_is_logging_handler(self):
        from app.ui.error_console import ErrorConsoleHandler
        h = ErrorConsoleHandler()
        assert isinstance(h, logging.Handler)

    def test_handler_default_level_warning(self):
        from app.ui.error_console import ErrorConsoleHandler
        h = ErrorConsoleHandler()
        assert h.level == logging.WARNING

    def test_handler_custom_level(self):
        from app.ui.error_console import ErrorConsoleHandler
        h = ErrorConsoleHandler(level=logging.ERROR)
        assert h.level == logging.ERROR


# ── ErrorConsoleWidget (requires QApplication) ─────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    """Minimal QApplication for widget tests."""
    import sys

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app


class TestErrorConsoleWidget:
    def test_instantiation(self, qapp):
        from app.ui.error_console import ErrorConsoleWidget
        w = ErrorConsoleWidget()
        assert w is not None

    def test_initial_error_count_is_zero(self, qapp):
        from app.ui.error_console import ErrorConsoleWidget
        w = ErrorConsoleWidget()
        assert w.error_count == 0

    def test_make_handler_returns_handler(self, qapp):
        from app.ui.error_console import ErrorConsoleWidget
        w = ErrorConsoleWidget()
        h = w.make_handler()
        assert isinstance(h, logging.Handler)

    def test_clear_resets_list(self, qapp):
        from app.ui.error_console import ErrorConsoleWidget
        w = ErrorConsoleWidget()
        # Simulate adding items by calling the internal slot directly
        w._on_record(logging.ERROR, "ERROR", "test error message")
        assert w._list.count() == 1
        w._clear()
        assert w._list.count() == 0
        assert w.error_count == 0

    def test_copy_all_puts_text_in_clipboard(self, qapp):
        from PySide6.QtWidgets import QApplication

        from app.ui.error_console import ErrorConsoleWidget
        w = ErrorConsoleWidget()
        w._on_record(logging.WARNING, "WARNING", "hello warning")
        w._copy_all()
        text = QApplication.clipboard().text()
        assert "hello warning" in text

    def test_error_increments_count(self, qapp):
        from app.ui.error_console import ErrorConsoleWidget
        w = ErrorConsoleWidget()
        w._on_record(logging.ERROR, "ERROR", "some error")
        assert w.error_count == 1
        w._on_record(logging.ERROR, "ERROR", "another error")
        assert w.error_count == 2

    def test_warning_does_not_increment_error_count(self, qapp):
        from app.ui.error_console import ErrorConsoleWidget
        w = ErrorConsoleWidget()
        w._on_record(logging.WARNING, "WARNING", "just a warning")
        assert w.error_count == 0
        assert w._list.count() == 1
