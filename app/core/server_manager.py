"""Server manager — auto-start and stop local TTS / LLM servers as subprocesses."""

from __future__ import annotations

import atexit
import logging
import subprocess
import sys
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _venv_python(venv_name: str) -> Path:
    """Return the Python executable inside a project-level venv."""
    if sys.platform == "win32":
        return _PROJECT_ROOT / venv_name / "Scripts" / "python.exe"
    return _PROJECT_ROOT / venv_name / "bin" / "python"


class _ManagedServer:
    """Wraps a subprocess for a local server."""

    def __init__(
        self,
        name: str,
        venv: str,
        script: str,
        args: list[str] | None = None,
        health_url: str = "",
    ):
        self.name = name
        self.venv = venv
        self.script = str(_PROJECT_ROOT / "scripts" / script)
        self.args = args or []
        self.health_url = health_url
        self._proc: subprocess.Popen | None = None  # type: ignore[type-arg]

    @property
    def python(self) -> Path:
        return _venv_python(self.venv)

    @property
    def is_venv_ready(self) -> bool:
        return self.python.exists()

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> bool:
        """Start the server subprocess. Returns True if started successfully."""
        if self.is_running:
            return True

        if not self.is_venv_ready:
            log.warning("%s: venv not found at %s", self.name, self.python)
            return False

        cmd = [str(self.python), self.script, *self.args]
        log.info("Starting %s: %s", self.name, " ".join(cmd))

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32"
                    else 0
                ),
            )
        except Exception as exc:
            log.error("Failed to start %s: %s", self.name, exc)
            return False

        return True

    def stop(self) -> None:
        """Terminate the server subprocess if running."""
        if self._proc is None:
            return
        if self._proc.poll() is None:
            log.info("Stopping %s (pid=%s)", self.name, self._proc.pid)
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def health_check(self) -> bool:
        """Probe the /health endpoint. Returns True if server is responsive."""
        if not self.health_url:
            return self.is_running
        try:
            resp = requests.get(self.health_url, timeout=3)
            return resp.status_code == 200
        except Exception:
            return False


class ServerManager:
    """Manages TTS and LLM local server lifecycles."""

    def __init__(
        self,
        tts_port: int = 8000,
        tts_model: str = "Qwen/Qwen3-TTS-0.6B",
        tts_device: str = "cpu",
        llm_port: int = 8001,
        llm_model: str = "Qwen3-0.6B",
        llm_device: str = "cpu",
    ):
        self.tts = _ManagedServer(
            name="TTS Server",
            venv="venv-tts",
            script="tts_server.py",
            args=["--port", str(tts_port), "--model-id", tts_model, "--device", tts_device],
            health_url=f"http://localhost:{tts_port}/health",
        )
        self.llm = _ManagedServer(
            name="LLM Server",
            venv="venv-llm",
            script="llm_server.py",
            args=["--port", str(llm_port), "--model-id", llm_model, "--device", llm_device],
            health_url=f"http://localhost:{llm_port}/health",
        )
        self._servers = [self.tts, self.llm]
        atexit.register(self.stop_all)

    def start_all(self) -> dict[str, bool]:
        """Start all servers. Returns {name: success}."""
        results = {}
        for srv in self._servers:
            # Skip if already accessible
            if srv.health_check():
                results[srv.name] = True
                log.info("%s already running", srv.name)
                continue
            results[srv.name] = srv.start()
        return results

    def stop_all(self) -> None:
        """Terminate all managed servers."""
        for srv in self._servers:
            srv.stop()

    def status(self) -> dict[str, dict]:
        """Return a dict of server status info."""
        info = {}
        for srv in self._servers:
            info[srv.name] = {
                "running": srv.is_running,
                "healthy": srv.health_check(),
                "venv_ready": srv.is_venv_ready,
            }
        return info
