"""Unified setup script replacing setup-tts.bat/sh, setup_asr.bat/sh, setup_llm.bat/sh.

Usage:
    python scripts/setup.py tts          # Setup TTS environment
    python scripts/setup.py asr          # Setup ASR environment
    python scripts/setup.py llm          # Setup LLM environment
    python scripts/setup.py all          # Setup all environments
    python scripts/setup.py app          # Setup main app environment
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VENV_MAP = {
    "app": ("venv", "requirements.txt"),
    "tts": ("venv-tts", "requirements-tts.txt"),
    "asr": ("venv-asr", "requirements-asr.txt"),
    "llm": ("venv-llm", "requirements-llm.txt"),
}

IS_WINDOWS = sys.platform == "win32"


def _python_cmd() -> str:
    """Return the base Python command available on this system."""
    for cmd in ("python3", "python"):
        try:
            subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                check=True,
            )
            return cmd
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    print("[ERROR] Python not found. Please install Python 3.10+.")
    sys.exit(1)


def _venv_python(venv_dir: Path) -> Path:
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_pip(venv_dir: Path) -> Path:
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def create_venv(name: str) -> Path:
    venv_name, req_file = VENV_MAP[name]
    venv_dir = PROJECT_ROOT / venv_name
    req_path = PROJECT_ROOT / req_file

    if not req_path.exists():
        print(f"[ERROR] {req_file} not found at {req_path}")
        sys.exit(1)

    python_cmd = _python_cmd()

    if venv_dir.exists():
        print(f"[INFO] {venv_name} already exists, skipping creation.")
    else:
        print(f"[INFO] Creating virtual environment: {venv_name}")
        subprocess.run([python_cmd, "-m", "venv", str(venv_dir)], check=True)

    venv_py = _venv_python(venv_dir)
    if not venv_py.exists():
        print(f"[ERROR] Python not found at {venv_py}")
        sys.exit(1)

    print(f"[INFO] Upgrading pip in {venv_name}...")
    subprocess.run(
        [str(venv_py), "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
    )

    print(f"[INFO] Installing dependencies from {req_file}...")
    subprocess.run(
        [str(venv_py), "-m", "pip", "install", "-r", str(req_path)],
        check=True,
    )

    print(f"[OK] {venv_name} setup complete.")
    return venv_dir


def setup_tts(*, launch: bool = True) -> None:
    """Setup TTS environment and optionally launch the server."""
    venv_dir = create_venv("tts")
    if launch:
        print("[INFO] Launching TTS server...")
        venv_py = _venv_python(venv_dir)
        server_script = PROJECT_ROOT / "scripts" / "tts_server.py"
        subprocess.Popen([str(venv_py), str(server_script)])
        print("[OK] TTS server started in background.")


def setup_asr() -> None:
    """Setup ASR environment."""
    create_venv("asr")


def setup_llm(*, launch: bool = True) -> None:
    """Setup LLM environment and optionally launch the server."""
    venv_dir = create_venv("llm")
    if launch:
        print("[INFO] Launching LLM server...")
        venv_py = _venv_python(venv_dir)
        server_script = PROJECT_ROOT / "scripts" / "llm_server.py"
        subprocess.Popen([str(venv_py), str(server_script)])
        print("[OK] LLM server started in background.")


def setup_app() -> None:
    """Setup main application environment."""
    create_venv("app")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Qwen3-TTS 環境設定工具",
    )
    parser.add_argument(
        "target",
        choices=["tts", "asr", "llm", "app", "all"],
        help="要設定的環境 (tts/asr/llm/app/all)",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="設定完成後不自動啟動伺服器",
    )
    args = parser.parse_args()

    targets = ["app", "tts", "asr", "llm"] if args.target == "all" else [args.target]

    for target in targets:
        print(f"\n{'='*60}")
        print(f"  Setting up: {target}")
        print(f"{'='*60}\n")
        if target == "tts":
            setup_tts(launch=not args.no_launch)
        elif target == "asr":
            setup_asr()
        elif target == "llm":
            setup_llm(launch=not args.no_launch)
        elif target == "app":
            setup_app()

    print("\n[DONE] All environments set up successfully.")


if __name__ == "__main__":
    main()
