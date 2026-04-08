"""Model manager — detect, download, and manage local Qwen3 models.

Provides non-blocking model download with progress reporting via Qt signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6 import QtCore

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MODELS_DIR = _PROJECT_ROOT / "models"


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for a downloadable model."""

    group: str  # "tts" | "asr" | "llm"
    repo_id: str  # e.g. "Qwen/Qwen3-TTS-0.6B"
    name: str  # e.g. "Qwen3-TTS-0.6B"
    description: str
    dir_name: str  # local directory name under models/


# Default 0.6B models that should be auto-installed
DEFAULT_MODELS: list[ModelInfo] = [
    ModelInfo(
        group="tts",
        repo_id="Qwen/Qwen3-TTS-0.6B",
        name="Qwen3-TTS-0.6B",
        description="語音合成模型（~1.2 GB）",
        dir_name="Qwen3-TTS-0.6B",
    ),
    ModelInfo(
        group="asr",
        repo_id="Qwen/Qwen3-ASR-0.6B",
        name="Qwen3-ASR-0.6B",
        description="語音辨識模型（~1.2 GB）",
        dir_name="Qwen3-ASR-0.6B",
    ),
    ModelInfo(
        group="llm",
        repo_id="Qwen/Qwen3-0.6B",
        name="Qwen3-0.6B",
        description="LLM 潤稿翻譯模型（~1.2 GB）",
        dir_name="Qwen3-0.6B",
    ),
]


def models_dir() -> Path:
    """Return the project-level models/ directory."""
    return _MODELS_DIR


def is_model_downloaded(model: ModelInfo) -> bool:
    """Check whether a model's local directory contains config.json."""
    return (_MODELS_DIR / model.dir_name / "config.json").exists()


def get_missing_models(models: list[ModelInfo] | None = None) -> list[ModelInfo]:
    """Return the subset of *models* that are not yet downloaded locally."""
    if models is None:
        models = DEFAULT_MODELS
    return [m for m in models if not is_model_downloaded(m)]


def local_model_path(dir_name: str) -> Path:
    """Return the absolute local path for a model directory."""
    return _MODELS_DIR / dir_name


# ── Download worker (runs in QThread) ─────────────────────────────────────────


class ModelDownloadWorker(QtCore.QObject):
    """Download one or more models via huggingface_hub in a background thread.

    Signals
    -------
    progress(model_name, downloaded_bytes, total_bytes)
    model_done(model_name)
    all_done()
    error(message)
    """

    progress = QtCore.Signal(str, int, int)  # name, current, total
    model_done = QtCore.Signal(str)
    all_done = QtCore.Signal()
    error = QtCore.Signal(str)

    def __init__(self, models: list[ModelInfo]):
        super().__init__()
        self._models = list(models)

    def run(self) -> None:
        try:
            from huggingface_hub import snapshot_download  # type: ignore[import]
        except ImportError:
            self.error.emit(
                "huggingface_hub 未安裝。\n"
                "請執行: pip install huggingface_hub"
            )
            return

        _MODELS_DIR.mkdir(parents=True, exist_ok=True)

        for model in self._models:
            if is_model_downloaded(model):
                self.model_done.emit(model.name)
                continue

            local_dir = _MODELS_DIR / model.dir_name
            local_dir.mkdir(parents=True, exist_ok=True)

            log.info("Downloading %s → %s", model.repo_id, local_dir)
            self.progress.emit(model.name, 0, 100)

            try:
                snapshot_download(
                    repo_id=model.repo_id,
                    local_dir=str(local_dir),
                    ignore_patterns=[
                        "*.msgpack",
                        "flax_model*",
                        "tf_model*",
                        "rust_model*",
                    ],
                )
            except Exception as exc:
                self.error.emit(f"下載 {model.name} 失敗：{exc}")
                return

            log.info("Download complete: %s", model.name)
            self.model_done.emit(model.name)

        self.all_done.emit()


def download_models_sync(models: list[ModelInfo]) -> list[str]:
    """Synchronous download (for scripts / CLI). Returns list of error messages."""
    errors: list[str] = []
    try:
        from huggingface_hub import snapshot_download  # type: ignore[import]
    except ImportError:
        return ["huggingface_hub 未安裝"]

    _MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for model in models:
        if is_model_downloaded(model):
            continue
        local_dir = _MODELS_DIR / model.dir_name
        local_dir.mkdir(parents=True, exist_ok=True)
        try:
            snapshot_download(
                repo_id=model.repo_id,
                local_dir=str(local_dir),
                ignore_patterns=["*.msgpack", "flax_model*", "tf_model*", "rust_model*"],
            )
        except Exception as exc:
            errors.append(f"{model.name}: {exc}")
    return errors


def get_gpu_info() -> str:
    """Return a short GPU description or 'CPU only'."""
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_mem
            return f"{name} ({mem / 1024**3:.1f} GB)"
        return "CPU only (CUDA 不可用)"
    except ImportError:
        return "CPU only (torch 未安裝)"
