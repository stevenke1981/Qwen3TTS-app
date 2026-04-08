"""Tests for app.core.config — Config, from_yaml, to_yaml."""

from pathlib import Path

from app.core.config import Config


class TestConfigDefaults:
    def test_default_config_has_expected_values(self):
        cfg = Config()
        assert cfg.api.qwen3_base_url == "http://localhost:8000"
        assert cfg.api.qwen3_timeout == 60
        assert cfg.ollama.base_url == "http://localhost:11434"
        assert cfg.audio.sample_rate == 22050
        assert cfg.ui.window_size == (960, 640)
        assert cfg.history.max_entries == 100

    def test_default_llm_provider_is_ollama(self):
        cfg = Config()
        assert cfg.llm.provider == "ollama"

    def test_default_asr_mode_is_local(self):
        cfg = Config()
        assert cfg.asr.mode == "local"


class TestConfigYaml:
    def test_roundtrip_yaml(self, tmp_path: Path):
        cfg = Config()
        cfg.api.qwen3_base_url = "http://example.com:9000"
        cfg.ui.window_size = (1280, 720)

        yaml_path = tmp_path / "test_config.yaml"
        cfg.to_yaml(yaml_path)

        loaded = Config.from_yaml(yaml_path)
        assert loaded.api.qwen3_base_url == "http://example.com:9000"
        assert loaded.ui.window_size == (1280, 720)

    def test_from_yaml_missing_keys_uses_defaults(self, tmp_path: Path):
        yaml_path = tmp_path / "partial.yaml"
        yaml_path.write_text("api:\n  qwen3_timeout: 30\n", encoding="utf-8")

        loaded = Config.from_yaml(yaml_path)
        assert loaded.api.qwen3_timeout == 30
        assert loaded.api.qwen3_base_url == "http://localhost:8000"  # default
        assert loaded.audio.sample_rate == 22050  # default

    def test_from_yaml_empty_file(self, tmp_path: Path):
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("", encoding="utf-8")

        loaded = Config.from_yaml(yaml_path)
        assert loaded.api.qwen3_base_url == "http://localhost:8000"
