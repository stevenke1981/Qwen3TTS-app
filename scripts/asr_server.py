"""Qwen3-ASR FastAPI Server — runs inside venv-asr.

Exposes the HTTP contract expected by ``app.api.asr_client.ASRClient``
when ``mode="server"``:

    GET  /health
    POST /asr          multipart: file=<audio bytes>
                       JSON:      {audio_b64, filename, language, timestamps}

Launch:
    python scripts/asr_server.py [--host HOST] [--port PORT]
                                 [--model-id MODEL_ID] [--device DEVICE]

Defaults:
    host     0.0.0.0
    port     8002
    model-id Qwen/Qwen3-ASR-0.6B
    device   cpu
"""

from __future__ import annotations

import argparse
import base64
import logging
import sys
import tempfile
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


import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

# ─── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("asr_server")

# ─── Global model ──────────────────────────────────────────────────────────────

_model = None          # Qwen3ASRModel instance, loaded once at startup
_model_id: str = ""
_device: str = "cpu"


def _load_model(model_id: str, device: str) -> None:
    """Import and initialise the Qwen3-ASR model."""
    global _model, _model_id, _device
    _model_id = model_id
    _device = device

    resolved = _resolve(model_id)
    log.info("Loading ASR model %s on %s …", resolved, device)
    try:
        from qwen_asr import Qwen3ASRModel  # type: ignore[import]
        _model = Qwen3ASRModel(model_id=resolved, device=device)
    except ImportError as exc:
        log.error(
            "Cannot import qwen_asr. "
            "Make sure you are running inside venv-asr: %s",
            exc,
        )
        sys.exit(1)
    log.info("ASR model loaded ✓")


# ─── Pydantic schemas ──────────────────────────────────────────────────────────

class ASRJsonRequest(BaseModel):
    audio_b64: str           # base64-encoded audio bytes
    filename: str = "audio.wav"
    language: str = ""       # "" → auto-detect
    timestamps: bool = True


class ASRResponse(BaseModel):
    text: str
    language: str = ""
    segments: list[dict] = []


# ─── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Qwen3-ASR Server", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": _model_id,
        "model_path": _resolve(_model_id),
        "device": _device,
    }


def _transcribe(audio_bytes: bytes, filename: str = "audio.wav",
                language: str = "", timestamps: bool = True) -> dict:
    """Write audio bytes to a temp file and call model.transcribe()."""
    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = _model.transcribe(  # type: ignore[union-attr]
            tmp_path,
            language=language or None,
            timestamps=timestamps,
        )
    except Exception as exc:
        log.exception("ASR transcription failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if isinstance(result, str):
        return {"text": result, "language": language, "segments": []}
    # result is expected to be a dict with at least "text"
    return {
        "text": result.get("text", ""),
        "language": result.get("language", language),
        "segments": result.get("segments", []),
    }


@app.post("/asr", response_model=ASRResponse)
async def asr_upload(file: UploadFile = File(...)) -> ASRResponse:
    """Transcribe audio from a multipart file upload."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    data = _transcribe(audio_bytes, filename=file.filename or "audio.wav")
    return ASRResponse(**data)


@app.post("/asr/json", response_model=ASRResponse)
def asr_json(req: ASRJsonRequest) -> ASRResponse:
    """Transcribe audio from a base64-encoded JSON body."""
    try:
        audio_bytes = base64.b64decode(req.audio_b64)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid base64 audio") from exc
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="audio_b64 decoded to empty bytes")
    data = _transcribe(audio_bytes, filename=req.filename,
                       language=req.language, timestamps=req.timestamps)
    return ASRResponse(**data)


# ─── Entry point ───────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Qwen3-ASR FastAPI server")
    p.add_argument("--host",     default="0.0.0.0")
    p.add_argument("--port",     type=int, default=8002)
    p.add_argument("--model-id", default="Qwen/Qwen3-ASR-0.6B")
    p.add_argument("--device",   default="cpu")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _load_model(args.model_id, args.device)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
