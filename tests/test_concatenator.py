"""Tests for app.audio.concatenator — audio chunk concatenation."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.audio.concatenator import concatenate_audio, concatenate_to_file


def _make_wav_bytes(samples: int = 16000, sr: int = 16000) -> bytes:
    """Create WAV bytes from silence for testing."""
    data = np.zeros(samples, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV")
    return buf.getvalue()


class TestConcatenateAudio:
    def test_single_chunk(self):
        chunk = _make_wav_bytes(16000)
        result = concatenate_audio([chunk])
        assert isinstance(result, bytes)
        audio, sr = sf.read(io.BytesIO(result), dtype="float32")
        assert sr == 16000
        assert len(audio) == 16000

    def test_two_chunks_with_gap(self):
        a = _make_wav_bytes(8000)
        b = _make_wav_bytes(8000)
        result = concatenate_audio([a, b], gap_ms=100)
        audio, sr = sf.read(io.BytesIO(result), dtype="float32")
        gap_samples = int(16000 * 0.1)
        expected_len = 8000 + gap_samples + 8000
        assert len(audio) == expected_len

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="No audio chunks"):
            concatenate_audio([])


class TestConcatenateToFile:
    def test_writes_output(self, tmp_path: Path):
        chunk = _make_wav_bytes(16000)
        out = tmp_path / "out.wav"
        result = concatenate_to_file([chunk], out)
        assert result == out
        assert out.exists()

    def test_empty_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="No audio chunks"):
            concatenate_to_file([], tmp_path / "out.wav")
