"""Qwen3-TTS Desktop Application - Entry Point"""

import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path so 'app' package is discoverable
# when the script is run directly (python app/main.py)
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import queue as _queue

from PySide6.QtCore import QSharedMemory, Qt, QThread, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.api.asr_client import ASRClient
from app.api.llm_client import LLMClient
from app.api.ollama_client import OllamaClient
from app.api.qwen3_client import Qwen3Client
from app.core.config import Config
from app.core.history import HistoryManager
from app.core.model_manager import ModelDownloadWorker, get_missing_models, models_dir
from app.core.server_manager import ServerManager
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme

log = logging.getLogger(__name__)


def _fmt_bytes(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024:.0f} KB"


def _dir_size(path: Path) -> int:
    """Return total bytes of all files under *path* (returns 0 if not found)."""
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except Exception:
        return 0


def _start_model_download(window: "MainWindow", missing: list, hf_token: str = "") -> None:
    """Launch a non-modal download dialog and background thread.

    The main window remains fully usable during installation.
    All worker signals are connected with Qt.QueuedConnection so that
    every callback executes on the main thread, preventing cross-thread
    timer / widget access warnings.
    A QTimer polls the local model directories every second for live MB display.
    """
    mdir = models_dir()

    # ── Non-modal progress dialog ──────────────────────────────────────────
    dlg = QDialog(window)
    dlg.setWindowTitle("模型安裝")
    dlg.setWindowModality(Qt.WindowModality.NonModal)
    dlg.setMinimumWidth(480)
    dlg.resize(520, 380)
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

    layout = QVBoxLayout(dlg)
    layout.setSpacing(8)
    layout.setContentsMargins(16, 16, 16, 12)

    name_label = QLabel("正在準備下載…")
    name_label.setWordWrap(True)

    bar = QProgressBar()
    bar.setRange(0, 0)      # indeterminate pulsing
    bar.setTextVisible(False)
    bar.setFixedHeight(10)

    size_label = QLabel(" ")
    size_label.setStyleSheet("color: #aaa; font-size: 11px;")

    # ── Log area ───────────────────────────────────────────────────────────
    log_box = QTextEdit()
    log_box.setReadOnly(True)
    log_box.setFont(log_box.font())  # inherit theme font
    log_box.setStyleSheet(
        "background:#12131e; color:#c8ccd4; font-family:Consolas,monospace;"
        "font-size:11px; border:1px solid #32334e; border-radius:4px;"
    )
    log_box.setMinimumHeight(200)

    btn_row = QHBoxLayout()
    cancel_btn = QPushButton("取消")
    cancel_btn.setFixedWidth(80)
    btn_row.addStretch()
    btn_row.addWidget(cancel_btn)

    layout.addWidget(name_label)
    layout.addWidget(bar)
    layout.addWidget(size_label)
    layout.addWidget(log_box)
    layout.addLayout(btn_row)
    dlg.show()

    # ── Background worker + thread ─────────────────────────────────────────
    worker = ModelDownloadWorker(missing, hf_token=hf_token)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)

    # ── Poll timer: drains msg_queue + updates dir size (runs on main thread) ─
    poll_timer = QTimer(dlg)
    poll_timer.setInterval(200)   # 200 ms — snappy log updates

    def _append_log(msg: str) -> None:
        log_box.append(msg)
        sb = log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _finish() -> None:
        """Called from main thread when worker signals finished."""
        poll_timer.stop()
        _drain_queue()   # flush any remaining messages

    def _drain_queue() -> None:
        """Process all pending messages from the worker queue."""
        while True:
            try:
                msg = worker.msg_queue.get_nowait()
            except _queue.Empty:
                break

            kind = msg[0]
            if kind == "log":
                _append_log(msg[1])
            elif kind == "progress":
                name_label.setText(f"正在下載：{msg[1]}…  {msg[2]}%")
            elif kind == "model_done":
                _append_log("")
            elif kind == "all_done":
                bar.setRange(0, 1)
                bar.setValue(1)
                name_label.setText("全部下載完成！")
                cancel_btn.setText("關閉")
                cancel_btn.clicked.disconnect()
                cancel_btn.clicked.connect(dlg.close)
                QMessageBox.information(
                    window, "完成", "所有模型下載完成，請重新啟動伺服器。"
                )
            elif kind == "error":
                err_msg = msg[1]
                _append_log(f"[錯誤] {err_msg}")
                name_label.setText("下載失敗")
                cancel_btn.setText("關閉")
                cancel_btn.clicked.disconnect()
                cancel_btn.clicked.connect(dlg.close)
                QMessageBox.warning(window, "下載錯誤", f"模型下載失敗：\n{err_msg}")

    def _poll() -> None:
        _drain_queue()
        total = sum(_dir_size(mdir / m.dir_name) for m in missing)
        if total > 0:
            size_label.setText(f"已下載：{_fmt_bytes(total)}")

    def _on_cancel() -> None:
        poll_timer.stop()
        thread.quit()
        dlg.close()

    poll_timer.timeout.connect(_poll)
    cancel_btn.clicked.connect(_on_cancel)
    # finished signal: safe single-arg QObject signal → reliable delivery
    worker.finished.connect(_finish)

    # Keep objects alive for the dialog's lifetime
    dlg._worker = worker           # type: ignore[attr-defined]
    dlg._thread = thread           # type: ignore[attr-defined]
    dlg._poll_timer = poll_timer   # type: ignore[attr-defined]

    poll_timer.start()
    thread.start()


def _prompt_and_download(window: "MainWindow") -> None:
    """Ask the user whether to download missing models, then start if yes."""
    missing = get_missing_models()
    if not missing:
        return

    names = "\n".join(f"  • {m.name}  ({m.description})" for m in missing)
    reply = QMessageBox.question(
        window,
        "模型缺失",
        f"以下本地模型尚未安裝：\n{names}\n\n是否立即下載？（約 2~5 GB）\n\n"
        "下載期間可繼續使用應用程式。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if reply == QMessageBox.StandardButton.Yes:
        _start_model_download(window, missing, window.config.tts_server.hf_token)


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

    # ── Auto-start local servers ─────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    server_manager = ServerManager(
        tts_port=config.tts_server.port,
        tts_model=config.tts_server.model_id,
        tts_device=config.tts_server.device,
        llm_port=config.llm_server.port,
        llm_model=config.llm_server.model_id,
        llm_device=config.llm_server.device,
        asr_port=config.asr_server.port,
        asr_model=config.asr_server.model_id,
        asr_device=config.asr_server.device,
    )
    if config.tts_server.auto_start or config.llm_server.auto_start or config.asr_server.auto_start:
        _servers_to_start = []
        if config.tts_server.auto_start:
            _servers_to_start.append(server_manager.tts)
        if config.llm_server.auto_start:
            _servers_to_start.append(server_manager.llm)
        if config.asr_server.auto_start:
            _servers_to_start.append(server_manager.asr)
        for _srv in _servers_to_start:
            if not _srv.health_check():
                _srv.start()
    else:
        pass  # all auto_start disabled

    qwen3_client = Qwen3Client(
        base_url=config.api.qwen3_base_url,
        timeout=config.api.qwen3_timeout,
        mode="auto",                            # server → local fallback
        venv_tts_dir=project_root / "venv-tts",
        device=config.tts_server.device,
        model_id=config.tts_server.model_id,
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

    # ── Check for missing models AFTER the main window is visible ───────────
    # 800 ms delay lets the window finish painting before the dialog appears
    QTimer.singleShot(800, lambda: _prompt_and_download(window))

    exit_code = app.exec()
    server_manager.stop_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
