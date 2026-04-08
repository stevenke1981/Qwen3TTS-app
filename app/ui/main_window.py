"""Main application window"""

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.app_logger import read_log_tail
from .asr_tab import ASRTab
from .clone_tab import CloneTab
from .edit_tab import EditTab
from .history_tab import HistoryTab
from .settings_tab import SettingsTab
from .text_tab import TextTab
from .theme import COLOR_ACCENT, COLOR_ERROR, COLOR_MUTED, COLOR_SUCCESS, FONT_SIZE_SM

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
    def __init__(self, config, qwen3_client, llm_client, history_manager, asr_client=None):
        super().__init__()
        self.config = config
        self.qwen3_client = qwen3_client
        self.llm_client = llm_client
        self.history_manager = history_manager
        self.asr_client = asr_client

        self._setup_ui()
        self._setup_status_bar()
        self._setup_tray()
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
            self.llm_client, self.qwen3_client, self.history_manager
        )
        self.asr_tab = ASRTab(self.asr_client)
        self.history_tab = HistoryTab(
            self.history_manager, self.text_tab, self.clone_tab
        )
        self.settings_tab = SettingsTab(self.config, asr_client=self.asr_client)

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

        self.ollama_dot = _StatusDot("LLM")
        self.status_bar.addPermanentWidget(self.ollama_dot)

    def _setup_tray(self):
        """Create system tray icon with context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self)
        # Use the window icon (or generate a text icon)
        icon = self.windowIcon()
        if icon.isNull():
            pix = QtGui.QPixmap(32, 32)
            pix.fill(QtGui.QColor(COLOR_ACCENT))
            icon = QIcon(pix)
        self._tray.setIcon(icon)
        self._tray.setToolTip("Qwen3-TTS 語音合成")

        tray_menu = QMenu()
        show_action = QAction("顯示主視窗", self)
        show_action.triggered.connect(self._restore_from_tray)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        quit_action = QAction("結束", self)
        quit_action.triggered.connect(QtWidgets.QApplication.quit)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, event):  # noqa: N802
        """Minimize to tray instead of quitting."""
        if hasattr(self, "_tray") and self._tray.isVisible():
            self.hide()
            self._tray.showMessage(
                "Qwen3-TTS",
                "應用程式已最小化至系統列",
                QSystemTrayIcon.MessageIcon.Information,
                1500,
            )
            event.ignore()
        else:
            event.accept()

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
        # F1 → shortcut overlay
        QShortcut(QKeySequence("F1"), self).activated.connect(self._show_shortcuts_dialog)
        # F12 → log viewer
        QShortcut(QKeySequence("F12"), self).activated.connect(self._show_log_viewer)
        # Ctrl+Q → quit
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._real_quit)

    def _real_quit(self):
        """Force-quit bypassing tray minimize."""
        if hasattr(self, "_tray"):
            self._tray.hide()
        QtWidgets.QApplication.quit()

    def _show_shortcuts_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("快捷鍵一覽")
        dlg.setMinimumSize(420, 360)
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(
            "<h3>全域快捷鍵</h3>"
            "<table cellpadding='4'>"
            "<tr><td><b>Ctrl+1…6</b></td><td>切換分頁</td></tr>"
            "<tr><td><b>Ctrl+H</b></td><td>歷史記錄</td></tr>"
            "<tr><td><b>Ctrl+,</b></td><td>設定</td></tr>"
            "<tr><td><b>F5</b></td><td>重新偵測連線</td></tr>"
            "<tr><td><b>F1</b></td><td>顯示此快捷鍵一覽</td></tr>"
            "<tr><td><b>F12</b></td><td>檢視應用程式日誌</td></tr>"
            "<tr><td><b>Ctrl+Q</b></td><td>完全退出</td></tr>"
            "</table>"
            "<h3>文字合成</h3>"
            "<table cellpadding='4'>"
            "<tr><td><b>Ctrl+Enter</b></td><td>開始合成</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>匯出音訊</td></tr>"
            "<tr><td><b>拖放 .txt/.md</b></td><td>載入文字檔</td></tr>"
            "</table>"
            "<h3>潤稿翻譯</h3>"
            "<table cellpadding='4'>"
            "<tr><td><b>Ctrl+Enter</b></td><td>傳送至合成</td></tr>"
            "</table>"
        )
        layout.addWidget(text)
        dlg.exec()

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
            ("ollama", self.llm_client.health_check),
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

    def _show_log_viewer(self):
        """Open a dialog showing recent application log entries."""
        dlg = QDialog(self)
        dlg.setWindowTitle("應用程式日誌")
        dlg.setMinimumSize(680, 480)
        layout = QVBoxLayout(dlg)
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setFontFamily("Consolas")
        log_text.setPlainText(read_log_tail(300))
        layout.addWidget(log_text)
        dlg.exec()
