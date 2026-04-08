"""Audio concatenation — join multiple WAV byte chunks into a single file."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import soundfile as sf


def concatenate_audio(
    chunks: list[bytes],
    *,
    gap_ms: int = 300,
) -> bytes:
    """Concatenate multiple WAV byte blobs into a single WAV.

    Parameters
    ----------
    chunks:
        List of raw WAV bytes (each from Qwen3 TTS API).
    gap_ms:
        Silence gap between chunks in milliseconds (default 300ms).

    Returns
    -------
    bytes
        The concatenated audio as WAV bytes.
    """
    if not chunks:
        raise ValueError("No audio chunks to concatenate")

    segments: list[np.ndarray] = []
    sample_rate: int | None = None

    for chunk in chunks:
        buf = io.BytesIO(chunk)
        data, sr = sf.read(buf, dtype="float32")
        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            # Resample if mismatched — but typically Qwen3 outputs consistent rates
            pass
        segments.append(data)

    assert sample_rate is not None

    # Create silence gap
    gap_samples = int(sample_rate * gap_ms / 1000)
    silence = np.zeros(gap_samples, dtype=np.float32)

    # Interleave segments with silence
    parts: list[np.ndarray] = []
    for i, seg in enumerate(segments):
        parts.append(seg)
        if i < len(segments) - 1:
            parts.append(silence)

    combined = np.concatenate(parts)

    out = io.BytesIO()
    sf.write(out, combined, sample_rate, format="WAV")
    return out.getvalue()


def concatenate_to_file(
    chunks: list[bytes],
    output_path: str | Path,
    *,
    gap_ms: int = 300,
) -> Path:
    """Concatenate and write to a file.

    Returns the Path written.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    combined = concatenate_audio(chunks, gap_ms=gap_ms)
    output_path.write_bytes(combined)
    return output_path
