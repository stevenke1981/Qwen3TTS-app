"""Qwen3-TTS API Client"""

import base64
from dataclasses import dataclass
from typing import BinaryIO

import requests

from .exceptions import TTSError, VoiceCloneError


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
    def __init__(self, base_url: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def synthesize(
        self,
        text: str,
        config: TTSConfig | None = None,
    ) -> bytes:
        if not text.strip():
            raise ValueError("Text cannot be empty")

        if config is None:
            config = TTSConfig()

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
        except requests.exceptions.Timeout as exc:
            raise TTSError("Request timed out", status_code=408) from exc
        except requests.exceptions.RequestException as e:
            raise TTSError(f"Request failed: {e}") from e

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
        except requests.exceptions.Timeout as exc:
            raise VoiceCloneError("Request timed out", status_code=408) from exc
        except requests.exceptions.RequestException as e:
            raise VoiceCloneError(f"Request failed: {e}") from e

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
        except requests.exceptions.Timeout as exc:
            raise VoiceCloneError("Request timed out", status_code=408) from exc
        except requests.exceptions.RequestException as e:
            raise VoiceCloneError(f"Request failed: {e}") from e

    def health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
