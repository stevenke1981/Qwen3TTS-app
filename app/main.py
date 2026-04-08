"""Qwen3-TTS Desktop Application - Entry Point"""

import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path so 'app' package is discoverable
# when the script is run directly (python app/main.py)
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from app.api.asr_client import ASRClient
from app.api.llm_client import LLMClient
from app.api.ollama_client import OllamaClient
from app.api.qwen3_client import Qwen3Client
from app.core.config import Config
from app.core.history import HistoryManager
from app.core.model_manager import ModelDownloadWorker, get_missing_models
from app.core.server_manager import ServerManager
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme

log = logging.getLogger(__name__)


def _check_and_download_models(app: QApplication) -> None:
    """If default 0.6B models are missing, offer to download them."""
    missing = get_missing_models()
    if not missing:
        return

    names = "\n".join(f"  • {m.name}" for m in missing)
    reply = QMessageBox.question(
        None,
        "模型缺失",
        f"以下本地模型尚未安裝：\n{names}\n\n是否立即下載？（約 2~5 GB）",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    if reply != QMessageBox.Yes:
        return

    progress = QProgressDialog("正在下載模型…", "取消", 0, 100)
    progress.setWindowTitle("模型安裝")
    progress.setMinimumDuration(0)
    progress.setValue(0)
    progress.setAutoClose(True)

    worker = ModelDownloadWorker(missing)

    def _on_progress(name: str, pct: int):
        progress.setLabelText(f"正在下載：{name} ({pct}%)")
        total_pct = int(pct / len(missing))  # rough approximation
        progress.setValue(min(total_pct, 99))

    def _on_model_done(name: str):
        log.info("模型下載完成：%s", name)

    def _on_all_done():
        progress.setValue(100)
        QMessageBox.information(None, "完成", "所有模型下載完成！")

    def _on_error(msg: str):
        progress.close()
        QMessageBox.warning(None, "下載錯誤", f"模型下載失敗：\n{msg}")

    worker.progress.connect(_on_progress)
    worker.model_done.connect(_on_model_done)
    worker.all_done.connect(_on_all_done)
    worker.error.connect(_on_error)

    from PySide6.QtCore import QThread

    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.all_done.connect(thread.quit)
    worker.error.connect(thread.quit)
    progress.canceled.connect(thread.quit)
    thread.start()

    # Block until download finishes (keeps event loop alive for progress updates)
    while thread.isRunning():
        app.processEvents()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Qwen3-TTS")
    app.setOrganizationName("Qwen3TTS")

    # ── Single-instance enforcement ──────────────────────────────────────────
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

    # ── Auto-install missing models ──────────────────────────────────────────
    _check_and_download_models(app)

    # ── Auto-start local servers ─────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    server_manager = ServerManager(
        tts_port=config.tts_server.port,
        tts_model=config.tts_server.model_id,
        tts_device=config.tts_server.device,
        llm_port=config.llm_server.port,
        llm_model=config.llm_server.model_id,
        llm_device=config.llm_server.device,
    )
    server_manager.start_all()

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
        venv_asr_dir=project_root / config.asr.venv_asr_path,
        device=config.asr.device,
        mode=config.asr.mode,
        api_url=config.asr.api_url,
        api_key=config.asr.api_key,
    )

    data_dir = project_root / "data"
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
        server_manager=server_manager,
    )
    window.show()

    exit_code = app.exec()
    server_manager.stop_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
