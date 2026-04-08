"""Error Console Widget — persistent panel showing WARNING/ERROR log messages.

Integrates with Python's ``logging`` module via ``ErrorConsoleHandler``.
Provides copy, clear, and auto-scroll capabilities.

Usage::

    console = ErrorConsoleWidget()
    logging.getLogger().addHandler(console.make_handler())
    # wire counter badge to status bar:
    console.error_count_changed.connect(lambda n: status_label.setText(f"⚠ {n}"))
"""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ─── Color constants ───────────────────────────────────────────────────────────

_COLOR_ERROR   = "#ef5350"
_COLOR_WARNING = "#ffa726"
_COLOR_INFO    = "#90caf9"

_LEVEL_COLORS: dict[int, str] = {
    logging.ERROR:    _COLOR_ERROR,
    logging.CRITICAL: _COLOR_ERROR,
    logging.WARNING:  _COLOR_WARNING,
    logging.INFO:     _COLOR_INFO,
}


# ─── Qt signal emitter (must be QObject for thread-safe signals) ───────────────

class _SignalEmitter(QObject):
    new_record = Signal(int, str, str)   # level, levelname, message


_emitter: _SignalEmitter | None = None


def _get_emitter() -> _SignalEmitter:
    global _emitter
    if _emitter is None:
        _emitter = _SignalEmitter()
    return _emitter


class ErrorConsoleHandler(logging.Handler):
    """logging.Handler that forwards records to ErrorConsoleWidget via Qt signals."""

    def __init__(self, level: int = logging.WARNING) -> None:
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            _get_emitter().new_record.emit(record.levelno, record.levelname, msg)
        except Exception:
            self.handleError(record)


# ─── Widget ────────────────────────────────────────────────────────────────────

class ErrorConsoleWidget(QWidget):
    """Persistent log panel showing WARNING / ERROR messages with copy support."""

    error_count_changed = Signal(int)   # emitted whenever the error count changes

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._error_count = 0
        self._setup_ui()
        _get_emitter().new_record.connect(self._on_record, Qt.ConnectionType.QueuedConnection)

    # ── Layout ─────────────────────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header bar
        header = QHBoxLayout()
        title = QLabel("🔴  錯誤訊息")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()

        self._copy_all_btn = QPushButton("複製全部")
        self._copy_all_btn.setToolTip("將全部訊息複製到剪貼板")
        self._copy_all_btn.clicked.connect(self._copy_all)
        self._copy_all_btn.setFixedHeight(24)
        header.addWidget(self._copy_all_btn)

        self._copy_sel_btn = QPushButton("複製選取")
        self._copy_sel_btn.setToolTip("複製選取的訊息")
        self._copy_sel_btn.clicked.connect(self._copy_selected)
        self._copy_sel_btn.setFixedHeight(24)
        header.addWidget(self._copy_sel_btn)

        self._clear_btn = QPushButton("清除")
        self._clear_btn.setToolTip("清除所有訊息")
        self._clear_btn.clicked.connect(self._clear)
        self._clear_btn.setFixedHeight(24)
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        # Message list
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setWordWrap(True)
        font = QFont("Consolas", 9)
        self._list.setFont(font)
        layout.addWidget(self._list)

    # ── Slots ──────────────────────────────────────────────────────────────────
    def _on_record(self, level: int, levelname: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        text = f"[{ts}] [{levelname}] {message}"
        item = QListWidgetItem(text)
        color = _LEVEL_COLORS.get(level, _COLOR_INFO)
        item.setForeground(QColor(color))
        self._list.addItem(item)
        self._list.scrollToBottom()

        if level >= logging.ERROR:
            self._error_count += 1
            self.error_count_changed.emit(self._error_count)

    def _copy_all(self) -> None:
        lines = [self._list.item(i).text() for i in range(self._list.count())]
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    def _copy_selected(self) -> None:
        items = self._list.selectedItems()
        if items:
            QApplication.clipboard().setText("\n".join(it.text() for it in items))

    def _clear(self) -> None:
        self._list.clear()
        self._error_count = 0
        self.error_count_changed.emit(0)

    # ── Public helpers ─────────────────────────────────────────────────────────
    @property
    def error_count(self) -> int:
        return self._error_count

    def make_handler(self, level: int = logging.WARNING) -> ErrorConsoleHandler:
        """Create and return a logging handler that feeds into this widget."""
        handler = ErrorConsoleHandler(level)
        handler.setFormatter(logging.Formatter("%(name)s — %(message)s"))
        return handler
