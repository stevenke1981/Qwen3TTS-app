"""Unified start script replacing start.bat/sh.

Usage:
    python scripts/start.py              # Start the app (auto-detect venv)
    python scripts/start.py --setup      # Setup venv first then start
    python scripts/start.py --check      # Only check connectivity
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = sys.platform == "win32"


def _venv_python(venv_name: str) -> Path:
    venv_dir = PROJECT_ROOT / venv_name
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _find_python() -> Path:
    """Find the best Python interpreter for the main app."""
    for venv in ("venv", ".venv"):
        py = _venv_python(venv)
        if py.exists():
            return py
    return Path(sys.executable)


def check_service(name: str, url: str, *, timeout: float = 3.0) -> bool:
    """Check if a service is reachable."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            print(f"  ✓ {name} is running at {url}")
            return True
    except requests.ConnectionError:
        pass
    except Exception:
        pass
    print(f"  ✗ {name} is NOT reachable at {url}")
    return False


def check_connectivity() -> dict[str, bool]:
    """Check all services."""
    print("\n[INFO] Checking service connectivity...\n")
    results = {
        "TTS Server": check_service("TTS Server", "http://localhost:8000/health"),
        "Ollama": check_service("Ollama", "http://localhost:11434/api/tags"),
        "LLM Server": check_service("LLM Server", "http://localhost:8001/health"),
    }
    return results


def start_app(python_path: Path) -> None:
    """Launch the main Qwen3-TTS application."""
    print(f"\n[INFO] Starting Qwen3-TTS app with: {python_path}\n")
    main_script = PROJECT_ROOT / "app" / "main.py"
    subprocess.run([str(python_path), str(main_script)], cwd=str(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Qwen3-TTS 啟動器")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="啟動前先安裝 / 更新依賴",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只檢查服務連線狀態，不啟動 App",
    )
    args = parser.parse_args()

    python_path = _find_python()

    if args.setup:
        setup_script = PROJECT_ROOT / "scripts" / "setup.py"
        subprocess.run([str(python_path), str(setup_script), "app"], check=True)
        python_path = _find_python()

    results = check_connectivity()

    if args.check:
        ok = all(results.values())
        print(f"\n{'[OK]' if ok else '[WARN]'} Connectivity check done.")
        sys.exit(0 if ok else 1)

    if not results.get("TTS Server"):
        print("\n[WARN] TTS server is not running. Voice synthesis will not work.")
        print("       Run: python scripts/setup.py tts")

    start_app(python_path)


if __name__ == "__main__":
    main()
