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


@dataclass
class Config:
    api: APIConfig = field(default_factory=APIConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Config":
        api_data     = data.get("api", {})
        ollama_data  = data.get("ollama", {})
        audio_data   = data.get("audio", {})
        ui_data      = data.get("ui", {})
        history_data = data.get("history", {})
        asr_data     = data.get("asr", {})

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
            audio=AudioConfig(**audio_data),
            ui=UIConfig(
                theme=ui_data.get("theme", "light"),
                window_size=tuple(ui_data.get("window_size", [960, 640])),
            ),
            history=HistoryConfig(**history_data),
            asr=ASRConfig(
                venv_asr_path=asr_data.get("venv_asr_path", "venv-asr"),
                model_id=asr_data.get("model_id", "Qwen/Qwen3-ASR-0.6B"),
                device=asr_data.get("device", "cpu"),
                timestamps=asr_data.get("timestamps", True),
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
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
