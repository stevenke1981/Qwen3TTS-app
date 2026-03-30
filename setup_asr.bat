@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo  Qwen3-TTS  —  ASR venv setup  (venv-asr)
echo ==================================================
echo.

REM ── Check Python ──────────────────────────────────
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Please install Python 3.10+ and retry.
    pause & exit /b 1
)

for /f "tokens=*" %%V in ('python --version 2^>^&1') do set PYVER=%%V
echo Using: %PYVER%

REM ── Create venv ───────────────────────────────────
if exist venv-asr (
    echo [INFO] venv-asr already exists – skipping creation.
) else (
    echo [INFO] Creating venv-asr ...
    python -m venv venv-asr
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause & exit /b 1
    )
)

REM ── Upgrade pip ───────────────────────────────────
echo [INFO] Upgrading pip ...
venv-asr\Scripts\python.exe -m pip install --upgrade pip --quiet

REM ── Install requirements ──────────────────────────
echo [INFO] Installing requirements-asr.txt ...
venv-asr\Scripts\pip.exe install -r requirements-asr.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.  Check requirements-asr.txt or network.
    pause & exit /b 1
)

REM ── Verify worker script ──────────────────────────
if not exist scripts\asr_worker.py (
    echo [WARN] scripts\asr_worker.py not found – did you run this from the project root?
)

echo.
echo ==================================================
echo  [OK]  venv-asr is ready.
echo        Open the app and go to the 🎧 語音辨識 tab.
echo ==================================================
pause
