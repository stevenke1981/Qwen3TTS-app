"""TTS Worker — runs under venv-tts interpreter.

Communication protocol:
  Input  : JSON on stdin
  Output : JSON on stdout (last line is the result)
  Progress: lines on stderr prefixed with  "PROGRESS:<stage>"

Request schema:
  {
    "op":          "tts" | "clone_text" | "clone_audio",
    "text":        "要合成的文字",
    "speed":       1.0,
    "format":      "wav",
    "model_id":    "Qwen/Qwen3-TTS-0.6B",
    "device":      "cpu",

    // clone_text only:
    "ref_text":    "參考文字",

    // clone_audio only:
    "ref_audio_b64": "<base64-encoded audio bytes>"
  }

Response schema:
  {
    "status":      "ok" | "error",
    "audio_b64":   "<base64-encoded audio bytes>",
    "sample_rate": 22050,
    "error":       null | "error message + traceback"
  }
"""

from __future__ import annotations

import base64
import gc
import io
import json
import sys
import traceback
from pathlib import Path

# ─── Local model resolution ───────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR   = _PROJECT_ROOT / "models"


def _resolve(repo_id: str) -> str:
    """Return local models/ path if the model was downloaded there, else repo_id."""
    name = repo_id.split("/")[-1]
    local = _MODELS_DIR / name
    if (local / "config.json").exists():
        return str(local)
    return repo_id


# ─── Progress helpers ─────────────────────────────────────────────────────────

def _progress(stage: str) -> None:
    print(f"PROGRESS:{stage}", file=sys.stderr, flush=True)


def _log(msg: str) -> None:
    print(f"LOG:{msg}", file=sys.stderr, flush=True)


# ─── Audio helpers ────────────────────────────────────────────────────────────

_FORMAT_SUBTYPE: dict[str, str] = {
    "wav":  "PCM_16",
    "flac": "PCM_16",
    "ogg":  "VORBIS",
}


def _to_bytes(audio, sample_rate: int, fmt: str) -> bytes:
    """Convert NumPy audio array to bytes in the requested format."""
    import numpy as np
    import soundfile as sf

    fmt = fmt.lower()
    buf = io.BytesIO()
    subtype = _FORMAT_SUBTYPE.get(fmt, "PCM_16")
    try:
        sf.write(buf, audio, sample_rate, format=fmt.upper(), subtype=subtype)
    except Exception:
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


# ─── Core TTS ─────────────────────────────────────────────────────────────────

def _load_model(model_id: str, device: str):
    """Load Qwen3TTS model (must run inside venv-tts)."""
    try:
        from qwen_tts import Qwen3TTS  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "qwen-tts 未安裝。請在 venv-tts 執行: pip install qwen-tts"
        ) from exc

    resolved = _resolve(model_id)
    _log(f"Loading model {resolved} on {device}")
    _progress("loading_model")
    model = Qwen3TTS(model_id=resolved, device=device)
    _progress("model_loaded")
    return model


def run_tts(
    text: str,
    model_id: str,
    device: str,
    speed: float,
    fmt: str,
) -> dict:
    model = _load_model(model_id, device)
    _progress("synthesizing")
    try:
        audio, sr = model.synthesize(text=text, speed=speed)
    except Exception as exc:
        raise RuntimeError(f"合成失敗：{exc}") from exc
    finally:
        del model
        gc.collect()
        _try_free_cuda(device)

    _progress("done")
    audio_bytes = _to_bytes(audio, sr, fmt)
    return {
        "status": "ok",
        "audio_b64": base64.b64encode(audio_bytes).decode(),
        "sample_rate": sr,
        "error": None,
    }


def run_clone_text(
    text: str,
    ref_text: str,
    model_id: str,
    device: str,
    speed: float,
    fmt: str,
) -> dict:
    model = _load_model(model_id, device)
    _progress("cloning")
    try:
        audio, sr = model.clone_from_text(text=text, ref_text=ref_text, speed=speed)
    except AttributeError:
        try:
            audio, sr = model.clone(text=text, ref_text=ref_text, speed=speed)
        except Exception as exc:
            raise RuntimeError(f"語音克隆失敗：{exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"語音克隆失敗：{exc}") from exc
    finally:
        del model
        gc.collect()
        _try_free_cuda(device)

    _progress("done")
    audio_bytes = _to_bytes(audio, sr, fmt)
    return {
        "status": "ok",
        "audio_b64": base64.b64encode(audio_bytes).decode(),
        "sample_rate": sr,
        "error": None,
    }


def run_clone_audio(
    text: str,
    ref_audio_b64: str,
    model_id: str,
    device: str,
    speed: float,
    fmt: str,
) -> dict:
    import numpy as np
    import soundfile as sf

    ref_bytes = base64.b64decode(ref_audio_b64)
    ref_array, ref_sr = sf.read(io.BytesIO(ref_bytes), dtype="float32")

    model = _load_model(model_id, device)
    _progress("cloning")
    try:
        audio, sr = model.clone_from_audio(
            text=text, ref_audio=ref_array, ref_sr=ref_sr, speed=speed
        )
    except AttributeError:
        try:
            audio, sr = model.clone(
                text=text, ref_wav=ref_array, ref_sr=ref_sr, speed=speed
            )
        except Exception as exc:
            raise RuntimeError(f"語音克隆失敗：{exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"語音克隆失敗：{exc}") from exc
    finally:
        del model
        gc.collect()
        _try_free_cuda(device)

    _progress("done")
    audio_bytes = _to_bytes(audio, sr, fmt)
    return {
        "status": "ok",
        "audio_b64": base64.b64encode(audio_bytes).decode(),
        "sample_rate": sr,
        "error": None,
    }


def _try_free_cuda(device: str) -> None:
    if device == "cpu":
        return
    try:
        import torch.cuda
        torch.cuda.empty_cache()
    except Exception:
        pass


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        print(json.dumps({"status": "error", "audio_b64": "", "error": "No input"}))
        return

    try:
        req: dict = json.loads(raw_input)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "error", "audio_b64": "", "error": str(exc)}))
        return

    op       = req.get("op", "tts")
    text     = req.get("text", "")
    speed    = float(req.get("speed", 1.0))
    fmt      = req.get("format", "wav")
    model_id = req.get("model_id", "Qwen/Qwen3-TTS-0.6B")
    device   = req.get("device", "cpu")

    try:
        if op == "tts":
            result = run_tts(text, model_id, device, speed, fmt)
        elif op == "clone_text":
            result = run_clone_text(
                text, req.get("ref_text", ""), model_id, device, speed, fmt
            )
        elif op == "clone_audio":
            result = run_clone_audio(
                text, req.get("ref_audio_b64", ""), model_id, device, speed, fmt
            )
        else:
            result = {"status": "error", "audio_b64": "", "error": f"Unknown op: {op}"}
    except Exception as exc:
        result = {
            "status": "error",
            "audio_b64": "",
            "sample_rate": 0,
            "error": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        }

    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
