"""Qwen3-TTS Desktop Application - Entry Point"""

import sys
from pathlib import Path

# Ensure project root is in sys.path so 'app' package is discoverable
# when the script is run directly (python app/main.py)
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication, QMessageBox

from app.api.asr_client import ASRClient
from app.api.llm_client import LLMClient
from app.api.ollama_client import OllamaClient
from app.api.qwen3_client import Qwen3Client
from app.core.config import Config
from app.core.history import HistoryManager
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Qwen3-TTS")
    app.setOrganizationName("Qwen3TTS")

    # ── Single-instance enforcement ──────────────────────────────────────────
    # QSharedMemory is released automatically when the process exits (Windows)
    # or when the QSharedMemory object is destroyed.
    _instance_lock = QSharedMemory("Qwen3TTS-App-Instance-v1")
    if not _instance_lock.create(1):
        QMessageBox.warning(
            None,
            "已在執行中",
            "Qwen3-TTS 應用程式已在執行中。\n請切換到已開啟的視窗。",
        )
        sys.exit(0)

    # Apply global dark theme + font (must be done before any widgets are shown)
    apply_theme(app)

    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        config = Config.from_yaml(config_path)
    else:
        config = Config()

    qwen3_client = Qwen3Client(
        base_url=config.api.qwen3_base_url,
        timeout=config.api.qwen3_timeout,
    )

    ollama_client = OllamaClient(
        base_url=config.ollama.base_url,
    )
    ollama_client.default_model = config.ollama.default_model

    llm_client = LLMClient(
        provider=config.llm.provider,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        model=config.llm.model,
    )

    asr_client = ASRClient(
        venv_asr_dir=Path(__file__).parent.parent / config.asr.venv_asr_path,
        device=config.asr.device,
        mode=config.asr.mode,
        api_url=config.asr.api_url,
        api_key=config.asr.api_key,
    )

    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    history_path = data_dir / "history.yaml"

    history_manager = HistoryManager(
        storage_path=history_path,
        max_entries=config.history.max_entries,
    )

    window = MainWindow(
        config=config,
        qwen3_client=qwen3_client,
        llm_client=llm_client,
        history_manager=history_manager,
        asr_client=asr_client,
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
