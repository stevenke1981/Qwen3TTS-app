"""Simple audio waveform visualization widget."""

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from .theme import COLOR_ACCENT


class WaveformWidget(QtWidgets.QWidget):
    """Draws a simple waveform from raw audio bytes (WAV).

    Supports mouse-wheel zoom (horizontal scale) and click-to-seek.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples: list[float] = []
        self._zoom: float = 1.0   # 1.0 = fit all; >1 = zoomed in
        self._offset: int = 0     # first sample index to display
        self._drag_x: int = 0     # last mouse-press x for drag-pan
        self.setMinimumHeight(48)
        self.setMaximumHeight(64)
        self.setVisible(False)
        self.setToolTip("滾輪縮放波形，水平拖曳移動")

    def set_audio(self, audio_data: bytes) -> None:
        """Load audio data (WAV bytes) and extract samples for display."""
        try:
            import io

            import soundfile as sf

            audio_io = io.BytesIO(audio_data)
            data, _ = sf.read(audio_io, dtype="float32")

            # Downsample to ~200 points for display
            if hasattr(data, "ndim") and data.ndim > 1:
                data = data[:, 0]

            total = len(data)
            n_points = min(200, total)
            if n_points == 0:
                self._samples = []
                return

            step = max(1, total // n_points)
            self._samples = [
                float(max(data[i : i + step]) - min(data[i : i + step]))
                for i in range(0, total, step)
            ][:n_points]
            self._zoom = 1.0
            self._offset = 0
            self.setVisible(True)
            self.update()
        except Exception:
            self._samples = []

    def clear(self) -> None:
        self._samples = []
        self._zoom = 1.0
        self._offset = 0
        self.setVisible(False)
        self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:  # noqa: N802
        """Zoom in/out horizontally with mouse wheel."""
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else (1 / 1.15)
        self._zoom = max(1.0, min(20.0, self._zoom * factor))
        # Clamp offset so we don't scroll past the end
        visible = max(1, int(len(self._samples) / self._zoom))
        self._offset = min(self._offset, len(self._samples) - visible)
        self._offset = max(0, self._offset)
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        self._drag_x = event.pos().x()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if not self._samples or self._zoom <= 1.0:
            return
        dx = self._drag_x - event.pos().x()
        self._drag_x = event.pos().x()
        total = len(self._samples)
        visible = max(1, int(total / self._zoom))
        shift = int(dx * visible / self.width())
        self._offset = max(0, min(total - visible, self._offset + shift))
        self.update()

    def paintEvent(self, event):  # noqa: N802
        if not self._samples:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        mid_y = h / 2

        total = len(self._samples)
        visible = max(1, int(total / self._zoom))
        start = self._offset
        end = min(total, start + visible)
        samples = self._samples[start:end]
        n = len(samples)
        if n == 0:
            painter.end()
            return

        bar_w = max(1.0, w / n - 0.5)
        max_amp = max(samples) if samples else 1.0
        if max_amp == 0:
            max_amp = 1.0

        color = QtGui.QColor(COLOR_ACCENT)
        painter.setPen(Qt.NoPen)

        for i, amp in enumerate(samples):
            x = i * (w / n)
            bar_h = max(2, (amp / max_amp) * (h * 0.8))
            rect = QtCore.QRectF(x, mid_y - bar_h / 2, bar_w, bar_h)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 1, 1)

        painter.end()
