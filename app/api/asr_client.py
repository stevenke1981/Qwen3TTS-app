"""ASR Client — bridges the main `venv` and the `venv-asr` interpreter.

The main app runs under `venv` (PySide6 + Qwen3-TTS). Because `qwen-asr`
pins a different `transformers` version than `qwen-tts`, they live in a
separate virtual environment called **`venv-asr`**.

This client spawns `venv-asr/Scripts/python.exe scripts/asr_worker.py`,
passes a JSON request on stdin, and parses the JSON result from stdout.
Progress messages arrive on stderr as ``PROGRESS:<stage>`` lines and are
forwarded to an optional callable so the UI can update a progress bar.

Usage (blocking, call from a QThread worker):
    client = ASRClient()
    result = client.transcribe(
        source="https://www.youtube.com/watch?v=xxx",
        source_type="url",
        language="Chinese",
        timestamps=True,
        progress_callback=lambda s: print("Progress:", s),
    )
    print(result.text)
    for seg in result.segments:
        print(f"{seg.start:.1f}s – {seg.end:.1f}s  {seg.text}")
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class ASRSegment:
    """One subtitle/timestamp segment."""
    text:  str
    start: float  # seconds, absolute from start of audio
    end:   float  # seconds


@dataclass
class ASRResult:
    """Full transcription result returned by :meth:`ASRClient.transcribe`."""
    text:     str
    language: str
    segments: list[ASRSegment] = field(default_factory=list)

    # ── Subtitle export helpers ──────────────────────────────────────────

    def to_srt(self) -> str:
        """Export segments as SRT subtitle text."""
        if not self.segments:
            return f"1\n00:00:00,000 --> 00:00:10,000\n{self.text}\n"
        lines: list[str] = []
        for i, seg in enumerate(self.segments, 1):
            lines.append(str(i))
            lines.append(
                f"{_fmt_srt(seg.start)} --> {_fmt_srt(seg.end)}"
            )
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    def to_vtt(self) -> str:
        """Export segments as WebVTT subtitle text."""
        if not self.segments:
            return f"WEBVTT\n\n00:00:00.000 --> 00:00:10.000\n{self.text}\n"
        lines: list[str] = ["WEBVTT", ""]
        for seg in self.segments:
            lines.append(
                f"{_fmt_vtt(seg.start)} --> {_fmt_vtt(seg.end)}"
            )
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    def to_txt(self) -> str:
        """Return plain transcript text."""
        return self.text


# ─── Format helpers ───────────────────────────────────────────────────────────

def _fmt_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp ``HH:MM:SS,mmm``."""
    ms = int(round((seconds % 1) * 1000))
    s  = int(seconds) % 60
    m  = (int(seconds) // 60) % 60
    h  = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_vtt(seconds: float) -> str:
    """Format seconds as VTT timestamp ``HH:MM:SS.mmm``."""
    ms = int(round((seconds % 1) * 1000))
    s  = int(seconds) % 60
    m  = (int(seconds) // 60) % 60
    h  = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# ─── Progress label mapping ───────────────────────────────────────────────────

_STAGE_LABELS: dict[str, str] = {
    "downloading":      "下載中…",
    "converting_audio": "轉換音訊…",
    "download_done":    "下載完成",
    "loading_model":    "載入模型…",
    "transcribing":     "語音辨識中…",
    "done":             "完成",
}


def stage_to_label(stage: str) -> str:
    """Map a raw ``PROGRESS:`` stage string to a human-readable Chinese label."""
    # Handle "downloading_42" style (percentage)
    if stage.startswith("downloading_"):
        pct = stage.split("_", 1)[1]
        return f"下載中… {pct}%"
    return _STAGE_LABELS.get(stage, stage)


# ─── Client ───────────────────────────────────────────────────────────────────

# Locate the worker script relative to this file
_WORKER_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "asr_worker.py"
)


class ASRClient:
    """Manages Qwen3-ASR via an isolated ``venv-asr`` subprocess.

    Parameters
    ----------
    venv_asr_dir:
        Path to the ``venv-asr`` directory.  Defaults to ``<project_root>/venv-asr``.
    device:
        Torch device string – ``"cpu"``, ``"cuda"``, or ``"cuda:0"``.
    """

    def __init__(
        self,
        venv_asr_dir: Path | str | None = None,
        device: str = "cpu",
    ) -> None:
        if venv_asr_dir is None:
            venv_asr_dir = Path(__file__).resolve().parent.parent.parent / "venv-asr"
        self.venv_asr_dir = Path(venv_asr_dir)
        self.device = device

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def python_exe(self) -> Path:
        """Path to the venv-asr Python interpreter."""
        if sys.platform == "win32":
            return self.venv_asr_dir / "Scripts" / "python.exe"
        return self.venv_asr_dir / "bin" / "python"

    def is_available(self) -> bool:
        """Return True when venv-asr is set up and the worker script exists."""
        return self.python_exe.exists() and _WORKER_SCRIPT.exists()

    def health_check(self) -> bool:
        """Lightweight check – identical to :meth:`is_available`."""
        return self.is_available()

    # ── Main entrypoint ─────────────────────────────────────────────────

    def transcribe(
        self,
        source: str,
        source_type: str = "file",
        model_id: str = "Qwen/Qwen3-ASR-0.6B",
        language: str = "auto",
        timestamps: bool = True,
        timeout: int = 900,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ASRResult:
        """Run Qwen3-ASR transcription in a subprocess under venv-asr.

        Parameters
        ----------
        source:       File path for ``source_type="file"``; URL for ``"url"``.
        source_type:  ``"file"`` or ``"url"``.
        model_id:     HuggingFace model repo, e.g. ``"Qwen/Qwen3-ASR-1.7B"``.
        language:     ``"auto"`` to auto-detect, or any supported language name.
        timestamps:   Whether to request word-level timestamps (ForcedAligner).
        timeout:      Max seconds to wait for the subprocess (default 900 = 15 min).
        progress_callback:
            Called with a human-readable Chinese progress label whenever a
            ``PROGRESS:`` line arrives on stderr.  Runs in the **calling** thread.

        Returns
        -------
        ASRResult
            Contains ``.text`` (full transcript), ``.language``, and
            ``.segments`` (list of :class:`ASRSegment`).

        Raises
        ------
        RuntimeError
            When venv-asr is not set up, the worker crashes, or ASR returns error.
        """
        if not self.is_available():
            raise RuntimeError(
                "venv-asr 環境未準備好。\n"
                "請先執行 setup_asr.bat（Windows）或 bash setup_asr.sh（Linux/Mac）。\n"
                f"Python 路徑：{self.python_exe}\n"
                f"Worker 路徑：{_WORKER_SCRIPT}"
            )

        request_json = json.dumps(
            {
                "type":       source_type,
                "source":     source,
                "model_id":   model_id,
                "language":   language,
                "timestamps": timestamps,
                "device":     self.device,
            },
            ensure_ascii=False,
        )

        try:
            proc = subprocess.Popen(
                [str(self.python_exe), str(_WORKER_SCRIPT)],
                stdin  = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                text   = True,
                encoding = "utf-8",
                errors   = "replace",
            )
            stdout_data, stderr_data = proc.communicate(
                input=request_json,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError(f"ASR 逾時（{timeout}秒）。請嘗試較短的音訊或使用 0.6B 模型。")
        except Exception as exc:
            raise RuntimeError(f"無法啟動 ASR 工作程序：{exc}") from exc

        # Forward progress messages from stderr
        if progress_callback and stderr_data:
            for line in stderr_data.splitlines():
                if line.startswith("PROGRESS:"):
                    stage = line[9:].strip()
                    progress_callback(stage_to_label(stage))

        # Find the last non-empty JSON line in stdout
        json_line = ""
        for line in reversed(stdout_data.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                json_line = line
                break

        if not json_line:
            short_stderr = stderr_data[-2000:] if len(stderr_data) > 2000 else stderr_data
            raise RuntimeError(
                f"ASR 工作程序無輸出。\nstderr 末尾：\n{short_stderr}"
            )

        try:
            data: dict = json.loads(json_line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"無法解析 ASR 輸出 JSON：{exc}\n原始：{json_line[:500]}") from exc

        if data.get("status") != "ok":
            err = data.get("error", "（無詳細訊息）")
            short = err[:1000] if len(err) > 1000 else err
            raise RuntimeError(f"ASR 工作程序回報錯誤：\n{short}")

        segments = [
            ASRSegment(
                text  = s["text"],
                start = float(s.get("start", 0.0)),
                end   = float(s.get("end", 0.0)),
            )
            for s in data.get("segments", [])
        ]

        return ASRResult(
            text     = data.get("text", ""),
            language = data.get("language", ""),
            segments = segments,
        )
