"""Qwen3-TTS API Client

Supports two backends:
  "server" — HTTP requests to a running tts_server.py (legacy default)
  "local"  — subprocess via scripts/tts_worker.py inside venv-tts
  "auto"   — try server first; if connection refused, fall back to local
"""

import base64
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import requests

from .exceptions import TTSError, VoiceCloneError

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_WORKER_SCRIPT = _PROJECT_ROOT / "scripts" / "tts_worker.py"


@dataclass
class TTSConfig:
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    format: str = "wav"


@dataclass
class CloneConfig:
    ref_text: str | None = None
    ref_audio: BinaryIO | None = None


class Qwen3Client:
    def __init__(
        self,
        base_url: str,
        timeout: int = 60,
        mode: str = "auto",
        venv_tts_dir: Path | str | None = None,
        device: str = "cpu",
        model_id: str = "Qwen/Qwen3-TTS-0.6B",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.mode = mode           # "server" | "local" | "auto"
        self.device = device
        self.model_id = model_id

        if venv_tts_dir is None:
            venv_tts_dir = _PROJECT_ROOT / "venv-tts"
        self.venv_tts_dir = Path(venv_tts_dir)

    # ── Backend selection helpers ──────────────────────────────────────────

    @property
    def _local_python(self) -> Path:
        if sys.platform == "win32":
            return self.venv_tts_dir / "Scripts" / "python.exe"
        return self.venv_tts_dir / "bin" / "python"

    def _is_local_available(self) -> bool:
        return self._local_python.exists() and _WORKER_SCRIPT.exists()

    def _should_use_local(self, connection_error: bool = False) -> bool:
        if self.mode == "local":
            return True
        if self.mode == "auto" and connection_error:
            return self._is_local_available()
        return False

    # ── Local subprocess helpers ───────────────────────────────────────────

    def _call_worker(self, request: dict) -> bytes:
        """Run tts_worker.py in venv-tts subprocess. Returns raw audio bytes."""
        if not self._is_local_available():
            raise TTSError(
                "venv-tts 環境未準備好。\n"
                "請先執行：python scripts/setup.py tts\n"
                f"Python 路徑：{self._local_python}"
            )

        request.setdefault("model_id", self.model_id)
        request.setdefault("device", self.device)

        try:
            proc = subprocess.run(
                [str(self._local_python), str(_WORKER_SCRIPT)],
                input=json.dumps(request, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise TTSError(f"TTS worker 逾時（{self.timeout}秒）") from exc
        except Exception as exc:
            raise TTSError(f"無法啟動 TTS worker：{exc}") from exc

        # Find last JSON line in stdout
        json_line = ""
        for line in reversed(proc.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                json_line = line
                break

        if not json_line:
            short_err = proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr
            raise TTSError(f"TTS worker 無輸出。\nstderr：\n{short_err}")

        try:
            data: dict = json.loads(json_line)
        except json.JSONDecodeError as exc:
            raise TTSError(f"無法解析 TTS worker 輸出：{exc}") from exc

        if data.get("status") != "ok":
            raise TTSError(data.get("error", "TTS worker 回報未知錯誤"))

        audio_b64 = data.get("audio_b64", "")
        if not audio_b64:
            raise TTSError("TTS worker 回傳空音訊")
        return base64.b64decode(audio_b64)

    # ── Public API ─────────────────────────────────────────────────────────

    def synthesize(self, text: str, config: TTSConfig | None = None) -> bytes:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if config is None:
            config = TTSConfig()

        if self.mode == "local":
            return self._call_worker({
                "op": "tts",
                "text": text,
                "speed": config.speed,
                "format": config.format,
            })

        payload = {
            "text": text,
            "speed": config.speed,
            "pitch": config.pitch,
            "volume": config.volume,
            "format": config.format,
        }
        try:
            response = requests.post(
                f"{self.base_url}/tts",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.ConnectionError as exc:
            if self._should_use_local(connection_error=True):
                return self._call_worker({
                    "op": "tts",
                    "text": text,
                    "speed": config.speed,
                    "format": config.format,
                })
            raise TTSError(
                f"無法連接到 TTS 伺服器（{self.base_url}）。\n"
                "請確認伺服器已啟動，或執行 python scripts/setup.py tts"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise TTSError("Request timed out", status_code=408) from exc
        except requests.exceptions.RequestException as exc:
            raise TTSError(f"Request failed: {exc}") from exc

    def clone_from_text(
        self,
        text: str,
        ref_text: str,
        config: TTSConfig | None = None,
    ) -> bytes:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if not ref_text.strip():
            raise ValueError("Reference text cannot be empty")
        if config is None:
            config = TTSConfig()

        if self.mode == "local":
            return self._call_worker({
                "op": "clone_text",
                "text": text,
                "ref_text": ref_text,
                "speed": config.speed,
                "format": config.format,
            })

        payload = {
            "text": text,
            "ref_text": ref_text,
            "speed": config.speed,
            "pitch": config.pitch,
            "volume": config.volume,
            "format": config.format,
        }
        try:
            response = requests.post(
                f"{self.base_url}/clone/text",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.ConnectionError as exc:
            if self._should_use_local(connection_error=True):
                return self._call_worker({
                    "op": "clone_text",
                    "text": text,
                    "ref_text": ref_text,
                    "speed": config.speed,
                    "format": config.format,
                })
            raise VoiceCloneError(
                f"無法連接到 TTS 伺服器（{self.base_url}）。\n"
                "請確認伺服器已啟動，或執行 python scripts/setup.py tts"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise VoiceCloneError("Request timed out", status_code=408) from exc
        except requests.exceptions.RequestException as exc:
            raise VoiceCloneError(f"Request failed: {exc}") from exc

    def clone_from_audio(
        self,
        text: str,
        ref_audio: BinaryIO,
        config: TTSConfig | None = None,
    ) -> bytes:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if config is None:
            config = TTSConfig()

        ref_audio_b64 = base64.b64encode(ref_audio.read()).decode("utf-8")

        if self.mode == "local":
            return self._call_worker({
                "op": "clone_audio",
                "text": text,
                "ref_audio_b64": ref_audio_b64,
                "speed": config.speed,
                "format": config.format,
            })

        payload = {
            "text": text,
            "ref_audio": ref_audio_b64,
            "speed": config.speed,
            "pitch": config.pitch,
            "volume": config.volume,
            "format": config.format,
        }
        try:
            response = requests.post(
                f"{self.base_url}/clone/audio",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.ConnectionError as exc:
            if self._should_use_local(connection_error=True):
                return self._call_worker({
                    "op": "clone_audio",
                    "text": text,
                    "ref_audio_b64": ref_audio_b64,
                    "speed": config.speed,
                    "format": config.format,
                })
            raise VoiceCloneError(
                f"無法連接到 TTS 伺服器（{self.base_url}）。\n"
                "請確認伺服器已啟動，或執行 python scripts/setup.py tts"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise VoiceCloneError("Request timed out", status_code=408) from exc
        except requests.exceptions.RequestException as exc:
            raise VoiceCloneError(f"Request failed: {exc}") from exc

    def health_check(self) -> bool:
        if self.mode == "local":
            return self._is_local_available()
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            if self.mode == "auto":
                return self._is_local_available()
            return False
