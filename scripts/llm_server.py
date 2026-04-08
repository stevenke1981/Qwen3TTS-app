"""本地 LLM FastAPI 伺服器 — 使用 Qwen3 模型提供 OpenAI-compatible API。

與 app 的 LLM 設定對應：
    provider:  fastapi
    base_url:  http://localhost:8001
    api_key:   （留空）
    model:     Qwen3-0.6B  （或 1.7B、4B）

端點：
    GET  /health                   → {"status":"ok","model":"...","device":"..."}
    GET  /v1/models                → {"data":[{"id":"Qwen3-0.6B"}]}
    POST /v1/chat/completions      → OpenAI-compatible 回應

啟動：
    venv-llm\\Scripts\\python.exe scripts\\llm_server.py
    venv-llm\\Scripts\\python.exe scripts\\llm_server.py --model-id Qwen3-1.7B --port 8001
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("llm_server")

# ─── Local model resolution ───────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR   = _PROJECT_ROOT / "models"


def _resolve(model_id: str) -> str:
    """Return local models/ path if downloaded, else treat as HF repo ID."""
    local = _MODELS_DIR / model_id
    if (local / "config.json").exists():
        return str(local)
    # Also check with Qwen/ prefix stripped
    name = model_id.split("/")[-1]
    local2 = _MODELS_DIR / name
    if (local2 / "config.json").exists():
        return str(local2)
    return model_id


# ─── Global model state ───────────────────────────────────────────────────────

_model      = None
_tokenizer  = None
_model_id: str = ""
_device: str   = "cpu"


def _load_model(model_id: str, device: str) -> None:
    global _model, _tokenizer, _model_id, _device
    _model_id = model_id
    _device   = device

    resolved = _resolve(model_id)
    log.info("Loading model %s on %s …", resolved, device)

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        log.error("transformers / torch not installed: %s", exc)
        sys.exit(1)

    dtype = torch.float32 if device == "cpu" else (
        torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    )

    _tokenizer = AutoTokenizer.from_pretrained(resolved, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(
        resolved,
        torch_dtype=dtype,
        device_map=device,
        trust_remote_code=True,
    )
    _model.eval()
    log.info("Model loaded ✓")


# ─── Inference ────────────────────────────────────────────────────────────────

def _chat(messages: list[dict], max_new_tokens: int = 1024, temperature: float = 0.7) -> str:
    import torch

    text = _tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,  # Qwen3 thinking mode off for speed
    )
    inputs = _tokenizer([text], return_tensors="pt").to(_device)

    with torch.no_grad():
        output_ids = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else 1.0,
            pad_token_id=_tokenizer.eos_token_id,
        )

    # Decode only the newly generated tokens
    new_ids = output_ids[0][len(inputs.input_ids[0]):]
    return _tokenizer.decode(new_ids, skip_special_tokens=True).strip()


# ─── FastAPI app ──────────────────────────────────────────────────────────────

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
except ImportError as exc:
    log.error("fastapi / uvicorn not installed: %s", exc)
    sys.exit(1)

app = FastAPI(title="Qwen3-LLM Server", version="1.0.0")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": _model_id, "device": _device}


# ── Models list ───────────────────────────────────────────────────────────────

@app.get("/v1/models")
def list_models() -> dict:
    return {
        "object": "list",
        "data": [{"id": _model_id, "object": "model", "owned_by": "local"}],
    }


# ── Chat completions ──────────────────────────────────────────────────────────

class _Message(BaseModel):
    role: str
    content: str


class _ChatRequest(BaseModel):
    model: str = ""
    messages: list[_Message]
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False


@app.post("/v1/chat/completions")
def chat_completions(req: _ChatRequest) -> JSONResponse:
    if _model is None:
        raise HTTPException(status_code=503, detail="模型尚未載入")
    if req.stream:
        raise HTTPException(status_code=501, detail="stream 模式尚未支援")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        reply = _chat(messages, max_new_tokens=req.max_tokens, temperature=req.temperature)
    except Exception as exc:
        log.exception("Inference failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse({
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "model": _model_id,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    })


# ─── Entry point ──────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="本地 Qwen3 LLM 伺服器")
    parser.add_argument("--model-id", default="Qwen3-0.6B",
                        help="模型名稱或 HF repo ID（預設：Qwen3-0.6B）")
    parser.add_argument("--host",   default="0.0.0.0")
    parser.add_argument("--port",   type=int, default=8001)
    parser.add_argument("--device", default="cpu",
                        help="cpu | cuda | cuda:0（預設：cpu）")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _load_model(model_id=args.model_id, device=args.device)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
