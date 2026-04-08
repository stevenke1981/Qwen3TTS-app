"""ASR Worker — runs under venv-asr interpreter.

Communication protocol:
  Input  : JSON on stdin
  Output : JSON on stdout (last line is the result)
  Progress: lines on stderr prefixed with  "PROGRESS:<stage>"

Request schema:
  {
    "type":       "file" | "url",
    "source":     "/path/to/audio.wav" | "https://...",
    "model_id":   "Qwen/Qwen3-ASR-0.6B"   (default)
                  "Qwen/Qwen3-ASR-1.7B"
    "language":   "auto" | "Chinese" | "English" | ...
    "timestamps": true | false,
    "device":     "cpu" | "cuda" | "cuda:0"
  }

Response schema:
  {
    "status":    "ok" | "error",
    "text":      "full transcript",
    "language":  "Chinese",
    "segments":  [{"text": "...", "start": 0.0, "end": 2.5}, ...],
    "error":     null | "error message + traceback"
  }
"""

from __future__ import annotations

import gc
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

# ─── Local model resolution ───────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR   = _PROJECT_ROOT / "models"


def _resolve(repo_id: str) -> str:
    """Return local models/ path if the model was downloaded there, else repo_id."""
    name = repo_id.split("/")[-1]          # "Qwen3-ASR-0.6B"
    local = _MODELS_DIR / name
    if (local / "config.json").exists():
        return str(local)
    return repo_id


# ─── Progress helpers ─────────────────────────────────────────────────────────

def _progress(stage: str) -> None:
    print(f"PROGRESS:{stage}", file=sys.stderr, flush=True)


def _log(msg: str) -> None:
    print(f"LOG:{msg}", file=sys.stderr, flush=True)


# ─── Download (yt-dlp + ffmpeg) ───────────────────────────────────────────────

def download_audio(url: str, outdir: str) -> str:
    """Download audio from any URL yt-dlp supports.

    Returns the path to the extracted WAV file (16 kHz mono preferred).

    Requires:
      pip install yt-dlp
      ffmpeg on PATH  (for audio post-processing)
    """
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp 未安裝。請在 venv-asr 執行: pip install yt-dlp"
        ) from exc

    out_template = os.path.join(outdir, "%(id)s.%(ext)s")

    ydl_opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        # Force 16 kHz mono (optimal for ASR)
        "postprocessor_args": {
            "FFmpegExtractAudio": ["-ar", "16000", "-ac", "1"],
        },
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_ydlp_progress_hook],
    }

    _progress("downloading")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id", "audio")
        wav_path = os.path.join(outdir, f"{video_id}.wav")
        if not os.path.exists(wav_path):
            # yt-dlp may have used a different filename; find the .wav
            for fn in os.listdir(outdir):
                if fn.endswith(".wav"):
                    wav_path = os.path.join(outdir, fn)
                    break

    _progress("download_done")
    return wav_path


def _ydlp_progress_hook(d: dict) -> None:
    status = d.get("status", "")
    if status == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
        downloaded = d.get("downloaded_bytes", 0)
        if total:
            pct = int(downloaded / total * 100)
            _progress(f"downloading_{pct}")
    elif status == "finished":
        _progress("converting_audio")


# ─── Segment helpers ──────────────────────────────────────────────────────────

_SENTENCE_ENDS = set("。！？.!?…")
_COMMA_LIKE    = set("，,；;")

# Soft ceiling for a single subtitle block (seconds)
_MAX_SEG_DURATION = 7.0

def _build_segments(time_stamps: list) -> list[dict]:
    """Aggregate token-level timestamps into subtitle-ready segments.

    Strategy:
    1. Break on sentence-ending punctuation (。！？.!?)
    2. Also break when segment duration exceeds _MAX_SEG_DURATION
    3. Merge very short dangling segments into the previous one.
    """
    if not time_stamps:
        return []

    segments: list[dict] = []
    buf_tokens: list = []

    def flush(buf: list) -> None:
        if not buf:
            return
        text = "".join(getattr(t, "text", "") for t in buf).strip()
        if not text:
            return
        segments.append({
            "text": text,
            "start": float(getattr(buf[0], "start_time", 0.0)),
            "end":   float(getattr(buf[-1], "end_time", 0.0)),
        })

    for token in time_stamps:
        buf_tokens.append(token)
        tok_text = getattr(token, "text", "")
        duration = (
            float(getattr(token, "end_time", 0.0)) -
            float(getattr(buf_tokens[0], "start_time", 0.0))
        ) if buf_tokens else 0.0

        # Break on sentence-ending punctuation or max duration exceeded
        if any(c in tok_text for c in _SENTENCE_ENDS) or duration >= _MAX_SEG_DURATION:
            flush(buf_tokens)
            buf_tokens = []

    flush(buf_tokens)  # remaining tokens

    # Merge trailing very-short segments (<0.5 s) into previous
    merged: list[dict] = []
    for seg in segments:
        if (merged and
                seg["end"] - seg["start"] < 0.5 and
                seg["start"] == merged[-1]["end"]):
            merged[-1]["text"] += seg["text"]
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)

    return merged


# ─── Core ASR ─────────────────────────────────────────────────────────────────

def run_asr(
    audio_path: str,
    model_id: str,
    language: str,
    timestamps: bool,
    device: str,
) -> dict:
    """Load model and transcribe audio file.

    Returns dict with keys: text, language, segments.
    """
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("torch 未安裝。請在 venv-asr 執行: pip install torch") from exc

    try:
        from qwen_asr import Qwen3ASRModel
    except ImportError as exc:
        raise RuntimeError(
            "qwen-asr 未安裝。請在 venv-asr 執行: pip install qwen-asr"
        ) from exc

    # Dtype selection
    if device == "cpu":
        dtype = torch.float32
    else:
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    load_kwargs: dict[str, Any] = {
        "dtype": dtype,
        "device_map": device,
        "max_new_tokens": 4096,
        "max_inference_batch_size": 1,
    }

    if timestamps:
        load_kwargs["forced_aligner"] = _resolve("Qwen/Qwen3-ForcedAligner-0.6B")
        load_kwargs["forced_aligner_kwargs"] = {
            "dtype": dtype,
            "device_map": device,
        }

    _progress("loading_model")
    model = Qwen3ASRModel.from_pretrained(_resolve(model_id), **load_kwargs)

    lang_arg = None if language == "auto" else language

    _progress("transcribing")
    results = model.transcribe(
        audio=audio_path,
        language=lang_arg,
        return_time_stamps=timestamps,
    )

    result = results[0]
    text: str = getattr(result, "text", "")
    detected_language: str = getattr(result, "language", language or "unknown")

    segments: list[dict] = []
    if timestamps:
        raw_ts = getattr(result, "time_stamps", None)
        if raw_ts:
            segments = _build_segments(raw_ts)

    # Explicit cleanup to avoid accumulating GPU memory between calls
    del model
    gc.collect()
    if device != "cpu":
        try:
            import torch.cuda
            torch.cuda.empty_cache()
        except Exception:
            pass

    _progress("done")
    return {
        "status": "ok",
        "text": text,
        "language": detected_language,
        "segments": segments,
    }


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        result = {"status": "error", "text": "", "language": "", "segments": [],
                  "error": "No input received on stdin"}
        print(json.dumps(result, ensure_ascii=False))
        return

    try:
        req: dict = json.loads(raw_input)
    except json.JSONDecodeError as exc:
        result = {"status": "error", "text": "", "language": "", "segments": [],
                  "error": f"Invalid JSON input: {exc}"}
        print(json.dumps(result, ensure_ascii=False))
        return

    src_type: str = req.get("type", "file")
    source: str   = req.get("source", "")
    model_id: str = req.get("model_id", "Qwen/Qwen3-ASR-0.6B")
    language: str = req.get("language", "auto")
    timestamps: bool = req.get("timestamps", True)
    device: str   = req.get("device", "cpu")

    tmpdir: str = tempfile.mkdtemp(prefix="qwen3asr_")
    audio_path: str = source

    try:
        if src_type == "url":
            audio_path = download_audio(source, tmpdir)
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"下載後找不到音訊檔案: {audio_path}")

        payload = run_asr(audio_path, model_id, language, timestamps, device)
        print(json.dumps(payload, ensure_ascii=False), flush=True)

    except Exception as exc:
        error_result = {
            "status": "error",
            "text": "",
            "language": language,
            "segments": [],
            "error": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        }
        print(json.dumps(error_result, ensure_ascii=False), flush=True)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
