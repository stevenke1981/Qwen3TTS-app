"""Audio playback using QSound"""

from PySide6 import QtMultimedia


class AudioPlayer:
    def __init__(self):
        self._player = QtMultimedia.QMediaPlayer()
        self._audio_output = QtMultimedia.QAudioOutput()
        self._player.setAudioOutput(self._audio_output)

    def play(self, audio_data: bytes) -> None:
        from PySide6.QtCore import QBuffer, QByteArray

        # 必須存為實例屬性，否則 QBuffer 會被 GC 導致播放崩潰
        self._buffer = QBuffer()
        self._buffer.setData(QByteArray(audio_data))
        self._buffer.open(QBuffer.ReadOnly)

        self._player.stop()
        self._player.setSourceDevice(self._buffer)
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def is_playing(self) -> bool:
        return self._player.playbackState() == QtMultimedia.QMediaPlayer.PlayingState

    def set_volume(self, volume: float) -> None:
        self._audio_output.setVolume(volume)

    def volume(self) -> float:
        return self._audio_output.volume()
