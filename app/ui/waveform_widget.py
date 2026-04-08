"""Simple audio waveform visualization widget."""

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from .theme import COLOR_ACCENT


class WaveformWidget(QtWidgets.QWidget):
    """Draws a simple waveform from raw audio bytes (WAV)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples: list[float] = []
        self.setMinimumHeight(48)
        self.setMaximumHeight(64)
        self.setVisible(False)

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
            self.setVisible(True)
            self.update()
        except Exception:
            self._samples = []

    def clear(self) -> None:
        self._samples = []
        self.setVisible(False)
        self.update()

    def paintEvent(self, event):
        if not self._samples:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        mid_y = h / 2
        n = len(self._samples)
        bar_w = max(1.0, w / n - 0.5)
        max_amp = max(self._samples) if self._samples else 1.0
        if max_amp == 0:
            max_amp = 1.0

        color = QtGui.QColor(COLOR_ACCENT)
        painter.setPen(Qt.NoPen)

        for i, amp in enumerate(self._samples):
            x = i * (w / n)
            bar_h = max(2, (amp / max_amp) * (h * 0.8))
            rect = QtCore.QRectF(x, mid_y - bar_h / 2, bar_w, bar_h)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 1, 1)

        painter.end()
