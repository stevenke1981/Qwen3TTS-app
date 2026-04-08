"""Structured application logger with file rotation.

Provides :func:`get_logger` for named loggers and :func:`read_log_tail` for
displaying recent log lines in the UI.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path("data")
_LOG_FILE = _LOG_DIR / "app.log"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_BACKUP_COUNT = 3
_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def _ensure_init() -> None:
    global _initialized  # noqa: PLW0603
    if _initialized:
        return
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
    root = logging.getLogger("app")
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``app`` namespace.

    >>> log = get_logger("tts")
    >>> log.info("synthesis started")
    """
    _ensure_init()
    return logging.getLogger(f"app.{name}")


def read_log_tail(lines: int = 200) -> str:
    """Return the last *lines* lines from the log file."""
    if not _LOG_FILE.exists():
        return ""
    all_lines = _LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(all_lines[-lines:])


def log_path() -> Path:
    """Return the absolute path of the log file."""
    _ensure_init()
    return _LOG_FILE.resolve()
