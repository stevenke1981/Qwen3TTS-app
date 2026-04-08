"""Tests for app.core.app_logger — structured logging."""

from __future__ import annotations

from pathlib import Path

from app.core.app_logger import get_logger, log_path, read_log_tail


class TestGetLogger:
    def test_returns_logger(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.app_logger._LOG_DIR", tmp_path)
        monkeypatch.setattr("app.core.app_logger._LOG_FILE", tmp_path / "test.log")
        monkeypatch.setattr("app.core.app_logger._initialized", False)
        log = get_logger("test")
        assert log.name == "app.test"

    def test_log_writes_to_file(self, tmp_path: Path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("app.core.app_logger._LOG_DIR", tmp_path)
        monkeypatch.setattr("app.core.app_logger._LOG_FILE", log_file)
        monkeypatch.setattr("app.core.app_logger._initialized", False)
        log = get_logger("write_test")
        log.info("hello from test")
        log.handlers[0].flush() if log.handlers else None
        # Flush all handlers on the root 'app' logger
        import logging
        for h in logging.getLogger("app").handlers:
            h.flush()
        content = log_file.read_text(encoding="utf-8")
        assert "hello from test" in content


class TestReadLogTail:
    def test_missing_file_returns_empty(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.app_logger._LOG_FILE", tmp_path / "missing.log")
        assert read_log_tail() == ""

    def test_reads_last_lines(self, tmp_path: Path, monkeypatch):
        log_file = tmp_path / "test.log"
        log_file.write_text("\n".join(f"line-{i}" for i in range(100)), encoding="utf-8")
        monkeypatch.setattr("app.core.app_logger._LOG_FILE", log_file)
        tail = read_log_tail(5)
        lines = tail.strip().split("\n")
        assert len(lines) == 5
        assert lines[-1] == "line-99"


class TestLogPath:
    def test_returns_path(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.app_logger._LOG_DIR", tmp_path)
        monkeypatch.setattr("app.core.app_logger._LOG_FILE", tmp_path / "test.log")
        monkeypatch.setattr("app.core.app_logger._initialized", False)
        p = log_path()
        assert isinstance(p, Path)
