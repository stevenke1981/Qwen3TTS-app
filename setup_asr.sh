#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo " Qwen3-TTS  —  ASR venv setup  (venv-asr)"
echo "=================================================="
echo

# ── Locate Python 3 ───────────────────────────────────
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
if [[ -z "$PYTHON" ]]; then
    echo "[ERROR] Python 3 not found in PATH."
    echo "        Please install Python 3.10+ and retry."
    exit 1
fi
echo "Using: $($PYTHON --version)"

# ── Create venv ───────────────────────────────────────
if [[ -d venv-asr ]]; then
    echo "[INFO] venv-asr already exists — skipping creation."
else
    echo "[INFO] Creating venv-asr ..."
    "$PYTHON" -m venv venv-asr
fi

# ── Upgrade pip ───────────────────────────────────────
echo "[INFO] Upgrading pip ..."
venv-asr/bin/python -m pip install --upgrade pip --quiet

# ── Install requirements ──────────────────────────────
echo "[INFO] Installing requirements-asr.txt ..."
venv-asr/bin/pip install -r requirements-asr.txt

# ── Check worker script ───────────────────────────────
if [[ ! -f scripts/asr_worker.py ]]; then
    echo "[WARN] scripts/asr_worker.py not found — run this from the project root."
fi

echo
echo "=================================================="
echo " [OK]  venv-asr is ready."
echo "       Open the app and go to the 🎧 語音辨識 tab."
echo "=================================================="
