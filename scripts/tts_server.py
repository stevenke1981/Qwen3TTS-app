"""Qwen3-TTS FastAPI Server — runs inside venv-tts.

Exposes the same HTTP contract expected by ``app.api.qwen3_client.Qwen3Client``:

    GET  /health
    POST /tts          {text, speed, pitch, volume, format}
    POST /clone/text   {text, ref_text, speed, pitch, volume, format}
    POST /clone/audio  {text, ref_audio (base64), speed, pitch, volume, format}

Launch:
    python scripts/tts_server.py [--host HOST] [--port PORT]
                                 [--model-id MODEL_ID] [--device DEVICE]

Defaults:
    host     0.0.0.0
    port     8000
    model-id Qwen/Qwen3-TTS-0.6B
    device   cpu
"""

from __future__ import annotations

import argparse
import base64
import io
import logging
import sys
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

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

# ─── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("tts_server")

# ─── Global model ──────────────────────────────────────────────────────────────

_model = None          # Qwen3TTS instance, loaded once at startup
_model_id: str = ""
_device: str = "cpu"


def _load_model(model_id: str, device: str) -> None:
    """Import and initialise the Qwen3-TTS model.

    The ``qwen_tts`` package is installed only inside *venv-tts*, so this
    import must run inside the correct interpreter.
    """
    global _model, _model_id, _device
    _model_id = model_id
    _device = device

    resolved = _resolve(model_id)
    log.info("Loading model %s on %s …", resolved, device)
    try:
        from qwen_tts import Qwen3TTS  # type: ignore[import]
        _model = Qwen3TTS(model_id=resolved, device=device)
    except ImportError as exc:
        log.error(
            "Cannot import qwen_tts. "
            "Make sure you are running inside venv-tts: %s",
            exc,
        )
        sys.exit(1)
    log.info("Model loaded ✓")


# ─── Audio helpers ─────────────────────────────────────────────────────────────

_FORMAT_SUBTYPE: dict[str, str] = {
    "wav":  "PCM_16",
    "flac": "PCM_16",
    "ogg":  "VORBIS",
    "mp3":  "MPEG_LAYER_III",  # soundfile writes via libsndfile; fallback below
}

_MIME: dict[str, str] = {
    "wav":  "audio/wav",
    "flac": "audio/flac",
    "ogg":  "audio/ogg",
    "mp3":  "audio/mpeg",
}


def _to_bytes(audio: np.ndarray, sample_rate: int, fmt: str) -> bytes:
    """Convert a NumPy audio array to bytes in the requested container format."""
    fmt = fmt.lower()
    buf = io.BytesIO()
    subtype = _FORMAT_SUBTYPE.get(fmt, "PCM_16")
    try:
        sf.write(buf, audio, sample_rate, format=fmt.upper(), subtype=subtype)
    except Exception:
        # Fallback: always write WAV
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


# ─── Pydantic schemas ──────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    speed: float = Field(default=1.0, ge=0.1, le=5.0)
    pitch: float = Field(default=1.0, ge=0.1, le=5.0)
    volume: float = Field(default=1.0, ge=0.1, le=5.0)
    format: str = Field(default="wav")
    speaker: str | None = None  # optional voice name / speaker ID


class CloneTextRequest(BaseModel):
    text: str
    ref_text: str
    speed: float = Field(default=1.0, ge=0.1, le=5.0)
    pitch: float = Field(default=1.0, ge=0.1, le=5.0)
    volume: float = Field(default=1.0, ge=0.1, le=5.0)
    format: str = Field(default="wav")


class CloneAudioRequest(BaseModel):
    text: str
    ref_audio: str  # base64-encoded audio bytes
    speed: float = Field(default=1.0, ge=0.1, le=5.0)
    pitch: float = Field(default=1.0, ge=0.1, le=5.0)
    volume: float = Field(default=1.0, ge=0.1, le=5.0)
    format: str = Field(default="wav")


# ─── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Qwen3-TTS Server", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": _model_id, "model_path": _resolve(_model_id), "device": _device}


@app.post("/tts")
def tts(req: TTSRequest) -> Response:
    """Basic text-to-speech synthesis."""
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    try:
        audio, sr = _model.synthesize(
            text=req.text,
            speaker=req.speaker,
            speed=req.speed,
        )
    except Exception as exc:
        log.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    audio_bytes = _to_bytes(audio, sr, req.format)
    mime = _MIME.get(req.format.lower(), "audio/wav")
    return Response(content=audio_bytes, media_type=mime)


@app.post("/clone/text")
def clone_text(req: CloneTextRequest) -> Response:
    """Voice cloning with reference text (no reference audio)."""
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    if not req.ref_text.strip():
        raise HTTPException(status_code=422, detail="ref_text must not be empty")

    try:
        audio, sr = _model.clone_from_text(
            text=req.text,
            ref_text=req.ref_text,
            speed=req.speed,
        )
    except AttributeError:
        # Older package versions may not expose clone_from_text; fallback.
        try:
            audio, sr = _model.clone(
                text=req.text,
                ref_text=req.ref_text,
                speed=req.speed,
            )
        except Exception as exc:
            log.exception("clone_text failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("clone_text failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    audio_bytes = _to_bytes(audio, sr, req.format)
    mime = _MIME.get(req.format.lower(), "audio/wav")
    return Response(content=audio_bytes, media_type=mime)


@app.post("/clone/audio")
def clone_audio(req: CloneAudioRequest) -> Response:
    """Voice cloning from reference audio bytes (base64-encoded)."""
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    if not req.ref_audio.strip():
        raise HTTPException(status_code=422, detail="ref_audio must not be empty")

    try:
        ref_bytes = base64.b64decode(req.ref_audio)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"ref_audio is not valid base64: {exc}"
        ) from exc

    # Decode reference audio array via soundfile
    try:
        ref_buf = io.BytesIO(ref_bytes)
        ref_array, ref_sr = sf.read(ref_buf, dtype="float32")
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Cannot decode ref_audio as audio: {exc}"
        ) from exc

    try:
        audio, sr = _model.clone_from_audio(
            text=req.text,
            ref_audio=ref_array,
            ref_sr=ref_sr,
            speed=req.speed,
        )
    except AttributeError:
        try:
            audio, sr = _model.clone(
                text=req.text,
                ref_wav=ref_array,
                ref_sr=ref_sr,
                speed=req.speed,
            )
        except Exception as exc:
            log.exception("clone_audio failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("clone_audio failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    audio_bytes = _to_bytes(audio, sr, req.format)
    mime = _MIME.get(req.format.lower(), "audio/wav")
    return Response(content=audio_bytes, media_type=mime)


# ─── Entry point ───────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qwen3-TTS FastAPI server (run inside venv-tts)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--model-id",
        default="Qwen/Qwen3-TTS-0.6B",
        help="HuggingFace model ID (default: Qwen/Qwen3-TTS-0.6B)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Inference device: cpu | cuda | cuda:0 (default: cpu)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of uvicorn worker processes (default: 1; use 1 for GPU)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _load_model(model_id=args.model_id, device=args.device)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info",
    )
