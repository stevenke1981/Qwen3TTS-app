"""Audio export utilities"""

import io
from pathlib import Path

import soundfile as sf


class AudioExporter:
    @staticmethod
    def to_wav(audio_data: bytes, output_path: str | Path) -> None:
        audio_io = io.BytesIO(audio_data)
        data, samplerate = sf.read(audio_io, dtype="float32")
        sf.write(str(output_path), data, samplerate, format="WAV")

    @staticmethod
    def to_mp3(audio_data: bytes, output_path: str | Path) -> None:
        """將音訊匯出為 MP3（需要安裝 pydub 與 ffmpeg）。"""
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise RuntimeError(
                "MP3 匯出需要 pydub 套件。請執行：pip install pydub\n"
                "另外需安裝 ffmpeg 並加入 PATH。"
            ) from exc

        audio_io = io.BytesIO(audio_data)
        data, samplerate = sf.read(audio_io, dtype="int16")


        if data.ndim == 1:
            channels = 1
            raw = data.tobytes()
        else:
            channels = data.shape[1]
            raw = data.tobytes()

        segment = AudioSegment(
            data=raw,
            sample_width=2,
            frame_rate=samplerate,
            channels=channels,
        )
        segment.export(str(output_path), format="mp3")

    @staticmethod
    def get_info(audio_data: bytes) -> dict:
        audio_io = io.BytesIO(audio_data)
        data, samplerate = sf.read(audio_io, dtype="float32")
        return {
            "duration": len(data) / samplerate,
            "sample_rate": samplerate,
            "channels": data.shape[1] if len(data.shape) > 1 else 1,
            "samples": len(data),
        }
