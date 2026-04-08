"""Tests for server_manager module."""

from app.core.server_manager import ServerManager


class TestServerManager:
    def test_init_creates_servers(self):
        sm = ServerManager()
        assert sm.tts is not None
        assert sm.llm is not None

    def test_status_returns_dict(self):
        sm = ServerManager()
        result = sm.status()
        assert isinstance(result, dict)
        assert "TTS Server" in result
        assert "LLM Server" in result

    def test_stop_all_is_safe_when_not_started(self):
        sm = ServerManager()
        sm.stop_all()  # Should not raise

    def test_status_keys(self):
        sm = ServerManager()
        result = sm.status()
        for name, info in result.items():
            assert "running" in info
            assert "healthy" in info
            assert "venv_ready" in info
