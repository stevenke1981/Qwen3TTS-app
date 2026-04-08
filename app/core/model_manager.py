"""Model manager — detect, download, and manage local Qwen3 models.

Worker ↔ UI communication uses a thread-safe queue.Queue instead of
Qt cross-thread signals, which are unreliable with Python closures.

Message protocol (tuples in msg_queue):
  ("log",        text: str)
  ("progress",   name: str, pct: int)
  ("model_done", name: str)
  ("all_done",)
  ("error",      message: str)
"""

from __future__ import annotations

import fnmatch
import logging
import queue
from dataclasses import dataclass
from pathlib import Path

from PySide6 import QtCore

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MODELS_DIR   = _PROJECT_ROOT / "models"

_IGNORE_PATTERNS = ["*.msgpack", "flax_model*", "tf_model*", "rust_model*"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_size(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


# ── Model metadata ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelInfo:
    group:       str   # "tts" | "asr" | "llm"
    repo_id:     str   # e.g. "Qwen/Qwen3-TTS-0.6B"
    name:        str   # e.g. "Qwen3-TTS-0.6B"
    description: str
    dir_name:    str   # local directory name under models/


DEFAULT_MODELS: list[ModelInfo] = [
    ModelInfo(
        group="tts",
        repo_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        name="Qwen3-TTS-0.6B-Base",
        description="語音合成基礎模型（需 HF Token）",
        dir_name="Qwen3-TTS-0.6B-Base",
    ),
    ModelInfo(
        group="tts",
        repo_id="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        name="Qwen3-TTS-0.6B-CustomVoice",
        description="自訂音色模型（需 HF Token）",
        dir_name="Qwen3-TTS-0.6B-CustomVoice",
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
    return _MODELS_DIR


def is_model_downloaded(model: ModelInfo) -> bool:
    return (_MODELS_DIR / model.dir_name / "config.json").exists()


def get_missing_models(models: list[ModelInfo] | None = None) -> list[ModelInfo]:
    if models is None:
        models = DEFAULT_MODELS
    return [m for m in models if not is_model_downloaded(m)]


def local_model_path(dir_name: str) -> Path:
    return _MODELS_DIR / dir_name


# ── Download worker ───────────────────────────────────────────────────────────

class ModelDownloadWorker(QtCore.QObject):
    """Download models in a background QThread.

    All progress is communicated via ``msg_queue`` (thread-safe queue.Queue).
    The ``finished`` signal fires exactly once when the worker exits (success
    or error) so the UI can schedule cleanup.
    """

    # Only ONE signal needed: notify main thread the queue has new items.
    # Avoids all cross-thread Python-closure signal unreliability.
    finished = QtCore.Signal()

    def __init__(self, models: list[ModelInfo], hf_token: str = "") -> None:
        super().__init__()
        self._models = list(models)
        self._hf_token = hf_token.strip() or None
        self.msg_queue: queue.Queue = queue.Queue()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _put(self, *args) -> None:
        self.msg_queue.put(args)
        log.debug("worker msg: %s", args[0])

    # ── Entry point (called in background thread) ─────────────────────────

    def run(self) -> None:
        try:
            self._download_all()
        except Exception as exc:
            self._put("error", f"未預期的錯誤：{exc}")
        finally:
            self.finished.emit()

    def _download_all(self) -> None:
        try:
            from huggingface_hub import HfApi  # type: ignore[import]
        except ImportError:
            self._put(
                "error",
                "huggingface_hub 未安裝。\n請執行: pip install huggingface_hub",
            )
            return

        import os

        _MODELS_DIR.mkdir(parents=True, exist_ok=True)

        hf_endpoint = os.environ.get("HF_ENDPOINT", "").strip() or None
        if hf_endpoint:
            self._put("log", f"[INFO] HF_ENDPOINT = {hf_endpoint}")

        # Token priority: explicit > HF_TOKEN env var
        hf_token = self._hf_token or os.environ.get("HF_TOKEN", "").strip() or None
        if hf_token:
            self._put("log", "[INFO] 使用 HuggingFace Token 認證")
        else:
            self._put("log", "[WARN] 未設定 HF Token — 私有/受限模型可能下載失敗")
            self._put("log", "       請至「設定 → TTS 設定」填入 HuggingFace Token")

        api = HfApi(endpoint=hf_endpoint, token=hf_token)

        for model in self._models:
            if is_model_downloaded(model):
                self._put("log",        f"[跳過] {model.name} 已存在，略過下載")
                self._put("model_done", model.name)
                continue

            ok = self._download_one(api, model, hf_endpoint, hf_token)
            if not ok:
                return  # error already queued

        self._put("all_done")

    def _download_one(
        self,
        api,
        model: ModelInfo,
        hf_endpoint: str | None,
        hf_token: str | None,
    ) -> bool:
        from huggingface_hub import hf_hub_download  # type: ignore[import]

        local_dir = _MODELS_DIR / model.dir_name
        local_dir.mkdir(parents=True, exist_ok=True)

        # ── Get file list ─────────────────────────────────────────────────
        self._put("log",      f"[連線] 查詢 {model.repo_id} 檔案清單…")
        self._put("progress", model.name, 0)
        try:
            siblings = api.model_info(
                repo_id=model.repo_id, files_metadata=True
            ).siblings or []
        except Exception as exc:
            err_str = str(exc)
            if "401" in err_str or "403" in err_str or "authentication" in err_str.lower():
                self._put(
                    "error",
                    f"{model.name} 需要授權才能下載。\n\n"
                    "請至 https://huggingface.co/ 申請帳號並取得 Access Token，\n"
                    "然後在「設定 → TTS 設定 → HuggingFace Token」填入。\n\n"
                    f"原始錯誤：{exc}",
                )
            else:
                self._put("error", f"無法取得 {model.name} 檔案清單：{exc}")
            return False

        files = [
            s for s in siblings
            if not any(fnmatch.fnmatch(s.rfilename, pat) for pat in _IGNORE_PATTERNS)
        ]
        total_bytes = sum(s.size or 0 for s in files)
        self._put("log", f"[INFO] {len(files)} 個檔案，共 {_fmt_size(total_bytes)}")
        self._put("log", f"[INFO] 儲存至：{local_dir}")

        # ── Download each file ────────────────────────────────────────────
        done_bytes = 0
        for idx, sibling in enumerate(files):
            fname = sibling.rfilename
            fsize = sibling.size or 0
            size_str = f" ({_fmt_size(fsize)})" if fsize else ""
            self._put("log", f"  [{idx + 1}/{len(files)}] {fname}{size_str}")
            pct = int(done_bytes / total_bytes * 100) if total_bytes else 0
            self._put("progress", model.name, pct)

            try:
                dl_kwargs: dict = {
                    "repo_id":   model.repo_id,
                    "filename":  fname,
                    "local_dir": str(local_dir),
                }
                if hf_endpoint:
                    dl_kwargs["endpoint"] = hf_endpoint
                if hf_token:
                    dl_kwargs["token"] = hf_token
                hf_hub_download(**dl_kwargs)
            except Exception as exc:
                err_str = str(exc)
                if "401" in err_str or "403" in err_str:
                    self._put(
                        "error",
                        f"授權失敗：無法下載 {fname}。\n"
                        "請確認 HuggingFace Token 正確，並已申請此模型的存取權限。\n"
                        f"模型頁面：https://huggingface.co/{model.repo_id}",
                    )
                else:
                    self._put("error", f"下載 {fname} 失敗：{exc}")
                return False

            done_bytes += fsize
            self._put("log", "       ✓ 完成")

        self._put("log",        f"[完成] {model.name} 全部下載完成")
        self._put("progress",   model.name, 100)
        self._put("model_done", model.name)
        return True


# ── Synchronous download (CLI / scripts) ──────────────────────────────────────

def download_models_sync(models: list[ModelInfo]) -> list[str]:
    """Synchronous download for scripts/CLI. Returns list of error messages."""
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
                ignore_patterns=_IGNORE_PATTERNS,
            )
        except Exception as exc:
            errors.append(f"{model.name}: {exc}")
    return errors


# ── GPU info ──────────────────────────────────────────────────────────────────

def get_gpu_info() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem  = torch.cuda.get_device_properties(0).total_memory
            return f"{name} ({mem / 1024**3:.1f} GB)"
        return "CPU only (CUDA 不可用)"
    except ImportError:
        return "CPU only (torch 未安裝)"
