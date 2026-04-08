"""Configuration management"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class APIConfig:
    qwen3_base_url: str = "http://localhost:8000"
    qwen3_timeout: int = 60
    verify_ssl: bool = True


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    default_model: str = "llama3.2:latest"


@dataclass
class LLMConfig:
    """Unified LLM provider config for 潤稿 / translate functions.

    provider:  ``"ollama"`` | ``"openai"`` | ``"fastapi"``
    """
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    api_key: str = ""
    model: str = "llama3.2:latest"


@dataclass
class AudioConfig:
    sample_rate: int = 22050
    format: str = "wav"


@dataclass
class UIConfig:
    theme: str = "light"
    window_size: tuple[int, int] = (960, 640)


@dataclass
class HistoryConfig:
    max_entries: int = 100


@dataclass
class ASRConfig:
    venv_asr_path: str = "venv-asr"
    model_id: str = "Qwen/Qwen3-ASR-0.6B"
    device: str = "cpu"
    timestamps: bool = True
    # API mode (remote OpenAI-compatible ASR endpoint)
    mode: str = "local"   # "local" | "api"
    api_url: str = ""
    api_key: str = ""


@dataclass
class TTSServerConfig:
    """Local TTS server (scripts/tts_server.py) config."""

    model_id: str = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
    device: str = "cpu"
    port: int = 8000
    auto_start: bool = True
    hf_token: str = ""   # HuggingFace Access Token for gated models


@dataclass
class LLMServerConfig:
    """Local LLM server (scripts/llm_server.py) config."""

    model_id: str = "Qwen3-0.6B"
    device: str = "cpu"
    port: int = 8001
    auto_start: bool = True


@dataclass
class ASRServerConfig:
    """Local ASR server (scripts/asr_server.py) config."""

    model_id: str = "Qwen/Qwen3-ASR-0.6B"
    device: str = "cpu"
    port: int = 8002
    auto_start: bool = True


@dataclass
class Config:
    """Top-level application configuration."""

    api: APIConfig = field(default_factory=APIConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    tts_server: TTSServerConfig = field(default_factory=TTSServerConfig)
    llm_server: LLMServerConfig = field(default_factory=LLMServerConfig)
    asr_server: ASRServerConfig = field(default_factory=ASRServerConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return cls()
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Config":
        api_data     = data.get("api", {})
        ollama_data  = data.get("ollama", {})
        llm_data     = data.get("llm", {})
        audio_data   = data.get("audio", {})
        ui_data      = data.get("ui", {})
        history_data = data.get("history", {})
        asr_data     = data.get("asr", {})
        tts_srv_data = data.get("tts_server", {})
        llm_srv_data = data.get("llm_server", {})
        asr_srv_data = data.get("asr_server", {})

        return cls(
            api=APIConfig(
                qwen3_base_url=api_data.get("qwen3_base_url", "http://localhost:8000"),
                qwen3_timeout=api_data.get("qwen3_timeout", 60),
                verify_ssl=api_data.get("verify_ssl", True),
            ),
            ollama=OllamaConfig(
                base_url=ollama_data.get("base_url", "http://localhost:11434"),
                default_model=ollama_data.get("default_model", "llama3.2:latest"),
            ),
            llm=LLMConfig(
                provider=llm_data.get("provider", "fastapi"),
                base_url=llm_data.get("base_url", "http://localhost:8001"),
                api_key=llm_data.get("api_key", ""),
                model=llm_data.get("model", "Qwen3-0.6B"),
            ),
            audio=AudioConfig(**audio_data),
            ui=UIConfig(
                theme=ui_data.get("theme", "dark"),
                window_size=tuple(ui_data.get("window_size", [960, 640])),
            ),
            history=HistoryConfig(**history_data),
            asr=ASRConfig(
                venv_asr_path=asr_data.get("venv_asr_path", "venv-asr"),
                model_id=asr_data.get("model_id", "Qwen/Qwen3-ASR-0.6B"),
                device=asr_data.get("device", "cpu"),
                timestamps=asr_data.get("timestamps", True),
                mode=asr_data.get("mode", "local"),
                api_url=asr_data.get("api_url", ""),
                api_key=asr_data.get("api_key", ""),
            ),
            tts_server=TTSServerConfig(
                model_id=tts_srv_data.get("model_id", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
                device=tts_srv_data.get("device", "cpu"),
                port=tts_srv_data.get("port", 8000),
                auto_start=tts_srv_data.get("auto_start", True),
                hf_token=tts_srv_data.get("hf_token", ""),
            ),
            llm_server=LLMServerConfig(
                model_id=llm_srv_data.get("model_id", "Qwen3-0.6B"),
                device=llm_srv_data.get("device", "cpu"),
                port=llm_srv_data.get("port", 8001),
                auto_start=llm_srv_data.get("auto_start", True),
            ),
            asr_server=ASRServerConfig(
                model_id=asr_srv_data.get("model_id", "Qwen/Qwen3-ASR-0.6B"),
                device=asr_srv_data.get("device", "cpu"),
                port=asr_srv_data.get("port", 8002),
                auto_start=asr_srv_data.get("auto_start", True),
            ),
        )

    def to_yaml(self, path: str | Path) -> None:
        data = {
            "api": {
                "qwen3_base_url": self.api.qwen3_base_url,
                "qwen3_timeout": self.api.qwen3_timeout,
                "verify_ssl": self.api.verify_ssl,
            },
            "ollama": {
                "base_url": self.ollama.base_url,
                "default_model": self.ollama.default_model,
            },
            "llm": {
                "provider": self.llm.provider,
                "base_url": self.llm.base_url,
                "api_key": self.llm.api_key,
                "model": self.llm.model,
            },
            "audio": {
                "sample_rate": self.audio.sample_rate,
                "format": self.audio.format,
            },
            "ui": {
                "theme": self.ui.theme,
                "window_size": list(self.ui.window_size),
            },
            "history": {
                "max_entries": self.history.max_entries,
            },
            "asr": {
                "venv_asr_path": self.asr.venv_asr_path,
                "model_id": self.asr.model_id,
                "device": self.asr.device,
                "timestamps": self.asr.timestamps,
                "mode": self.asr.mode,
                "api_url": self.asr.api_url,
                "api_key": self.asr.api_key,
            },
            "tts_server": {
                "model_id": self.tts_server.model_id,
                "device": self.tts_server.device,
                "port": self.tts_server.port,
                "auto_start": self.tts_server.auto_start,
                "hf_token": self.tts_server.hf_token,
            },
            "llm_server": {
                "model_id": self.llm_server.model_id,
                "device": self.llm_server.device,
                "port": self.llm_server.port,
                "auto_start": self.llm_server.auto_start,
            },
            "asr_server": {
                "model_id": self.asr_server.model_id,
                "device": self.asr_server.device,
                "port": self.asr_server.port,
                "auto_start": self.asr_server.auto_start,
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
