"""Main application window"""

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (
    QTabWidget, QMessageBox, QLabel, QStatusBar, QHBoxLayout, QWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from .text_tab import TextTab
from .clone_tab import CloneTab
from .edit_tab import EditTab
from .history_tab import HistoryTab
from .settings_tab import SettingsTab
from .asr_tab import ASRTab
from .theme import COLOR_SUCCESS, COLOR_ERROR, COLOR_MUTED, COLOR_ACCENT, FONT_SIZE_SM

# ── Tab labels with Unicode icons ─────────────────────────────────────────────
_TAB_LABELS = [
    ("🎙  文字合成", "文字合成"),
    ("🎤  語音克隆", "語音克隆"),
    ("✏  潤稿翻譯", "潤稿翻譯"),
    ("🎧  語音辨識", "語音辨識"),
    ("📋  歷史記錄", "歷史記錄"),
    ("⚙  設定",     "設定"),
]


class _StatusDot(QWidget):
    """A tiny coloured circle that represents a service connection status."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._color = COLOR_MUTED
        self.setFixedSize(80, 20)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._dot = QLabel("●")
        self._dot.setFixedSize(14, 14)
        self._dot.setAlignment(Qt.AlignCenter)
        self._dot.setStyleSheet(f"color: {self._color}; font-size: 10px; background: transparent;")

        self._lbl = QLabel(label)
        self._lbl.setStyleSheet(f"color: {COLOR_MUTED}; font-size: {FONT_SIZE_SM}px; background: transparent;")

        layout.addWidget(self._dot)
        layout.addWidget(self._lbl)

    def set_connected(self, ok: bool | None) -> None:
        """ok=True → green, ok=False → red, ok=None → grey (unknown)."""
        if ok is True:
            color = COLOR_SUCCESS
            tooltip = "已連線"
        elif ok is False:
            color = COLOR_ERROR
            tooltip = "未連線"
        else:
            color = COLOR_MUTED
            tooltip = "未知"
        self._dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
        self._dot.setToolTip(tooltip)
        self._lbl.setToolTip(tooltip)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, qwen3_client, ollama_client, history_manager, asr_client=None):
        super().__init__()
        self.config = config
        self.qwen3_client = qwen3_client
        self.ollama_client = ollama_client
        self.history_manager = history_manager
        self.asr_client = asr_client

        self._setup_ui()
        self._setup_status_bar()
        self._connect_signals()
        self._setup_shortcuts()
        # Probe connection status after a short delay (non-blocking)
        QTimer.singleShot(1500, self._probe_connections)

    def _setup_ui(self):
        self.setWindowTitle("Qwen3-TTS 語音合成")
        self.resize(*self.config.ui.window_size)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(0)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        self.text_tab = TextTab(self.qwen3_client, self.history_manager)
        self.clone_tab = CloneTab(self.qwen3_client, self.history_manager)
        self.edit_tab = EditTab(
            self.ollama_client, self.qwen3_client, self.history_manager
        )
        self.asr_tab = ASRTab(self.asr_client)
        self.history_tab = HistoryTab(
            self.history_manager, self.text_tab, self.clone_tab
        )
        self.settings_tab = SettingsTab(self.config)

        for tab_obj, (icon_label, _) in zip(
            [self.text_tab, self.clone_tab, self.edit_tab,
             self.asr_tab, self.history_tab, self.settings_tab],
            _TAB_LABELS,
        ):
            tabs.addTab(tab_obj, icon_label)

        self.tabs = tabs

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Left: status text
        self.status_label = QLabel("就緒")
        self.status_bar.addWidget(self.status_label, 1)

        # Right: service connection dots
        sep = QLabel(" │ ")
        sep.setStyleSheet(f"color: {COLOR_MUTED}; background: transparent; font-size: {FONT_SIZE_SM}px;")
        self.status_bar.addPermanentWidget(sep)

        self.qwen3_dot = _StatusDot("Qwen3")
        self.status_bar.addPermanentWidget(self.qwen3_dot)

        sep2 = QLabel(" ")
        sep2.setStyleSheet("background: transparent;")
        self.status_bar.addPermanentWidget(sep2)

        self.ollama_dot = _StatusDot("Ollama")
        self.status_bar.addPermanentWidget(self.ollama_dot)

    def _connect_signals(self):
        self.edit_tab.text_sent.connect(self._on_text_sent_to_tts)
        self.edit_tab.text_sent_to_clone.connect(self._on_text_sent_to_clone)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _setup_shortcuts(self):
        # Ctrl+1..6 → switch tabs
        for i in range(6):
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda idx=i: self.tabs.setCurrentIndex(idx))

        # Ctrl+H → history tab (index 4)
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(
            lambda: self.tabs.setCurrentIndex(4)
        )
        # Ctrl+, → settings tab (index 5)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(
            lambda: self.tabs.setCurrentIndex(5)
        )
        # F5 → refresh connections
        QShortcut(QKeySequence("F5"), self).activated.connect(self._probe_connections)

    def _probe_connections(self):
        """Check both API endpoints in background and update the status LEDs."""
        class _Probe(QtCore.QObject):
            done = QtCore.Signal(str, bool)

            def __init__(self, name, fn):
                super().__init__()
                self._name = name
                self._fn = fn

            def run(self):
                try:
                    ok = self._fn()
                except Exception:
                    ok = False
                self.done.emit(self._name, ok)

        for name, fn in [
            ("qwen3", self.qwen3_client.health_check),
            ("ollama", self.ollama_client.health_check),
        ]:
            thread = QtCore.QThread(self)
            probe = _Probe(name, fn)
            probe.moveToThread(thread)
            probe.done.connect(self._on_probe_done)
            thread.started.connect(probe.run)
            probe.done.connect(thread.quit)
            thread.start()
            # Keep reference so GC doesn't collect them
            setattr(self, f"_probe_thread_{name}", thread)
            setattr(self, f"_probe_obj_{name}", probe)

    def _on_probe_done(self, name: str, ok: bool):
        if name == "qwen3":
            self.qwen3_dot.set_connected(ok)
            self.set_status(f"Qwen3 {'已連線' if ok else '未連線'}")
        elif name == "ollama":
            self.ollama_dot.set_connected(ok)

    def _on_tab_changed(self, index: int):
        if self.tabs.widget(index) is self.asr_tab:
            self.asr_tab._refresh_availability()
        if self.tabs.widget(index) is self.history_tab:
            self.history_tab.refresh()

    def _on_text_sent_to_tts(self, text: str):
        self.text_tab.text_input.setPlainText(text)
        self.tabs.setCurrentIndex(0)

    def _on_text_sent_to_clone(self, text: str):
        self.clone_tab.text_input.setPlainText(text)
        self.tabs.setCurrentIndex(1)

    def set_status(self, message: str):
        self.status_label.setText(message)


    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)
