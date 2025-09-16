"""Run WhisperX transcriptions from Python."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional

LOGGER = logging.getLogger(__name__)


class WhisperXTranscriber:
    """A minimal wrapper around the WhisperX CLI."""

    def __init__(
        self,
        *,
        whisperx_command: str = "whisperx",
        device: str = "cuda",
        model: str = "large-v3",
        compute_type: Optional[str] = None,
        extra_args: Optional[Iterable[str]] = None,
    ) -> None:
        self.whisperx_command = whisperx_command
        self.device = device
        self.model = model
        self.compute_type = compute_type
        self.extra_args = list(extra_args or [])

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: Optional[str] = None,
        translate: bool = True,
        output_dir: Optional[Path] = None,
    ) -> str:
        """Transcribe ``audio_path`` and return the resulting text."""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file '{audio_path}' not found")

        if shutil.which(self.whisperx_command) is None:
            raise FileNotFoundError(
                f"Unable to locate the '{self.whisperx_command}' executable. "
                "Ensure that WhisperX is installed inside your active Conda environment."
            )

        temp_dir: Optional[tempfile.TemporaryDirectory[str]] = None
        if output_dir is None:
            temp_dir = tempfile.TemporaryDirectory(prefix="whisperx_")
            workdir = Path(temp_dir.name)
        else:
            workdir = Path(output_dir)
            workdir.mkdir(parents=True, exist_ok=True)

        cmd: List[str] = [
            self.whisperx_command,
            str(audio_path),
            "--device",
            self.device,
            "--model",
            self.model,
            "--output_dir",
            str(workdir),
            "--output_format",
            "txt",
        ]
        if translate:
            cmd += ["--task", "translate"]
        if language:
            cmd += ["--language", language]
        if self.compute_type:
            cmd += ["--compute_type", self.compute_type]
        cmd.extend(self.extra_args)

        LOGGER.debug("Running WhisperX command: %s", " ".join(cmd))
        try:
            try:
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:  # pragma: no cover - passthrough
                LOGGER.error("WhisperX transcription failed: %s", exc.stderr)
                raise RuntimeError(
                    "WhisperX transcription failed. See the console output for details."
                ) from exc

            LOGGER.debug("WhisperX stdout: %s", result.stdout)
            LOGGER.debug("WhisperX stderr: %s", result.stderr)

            txt_files = sorted(workdir.glob("*.txt"))
            if not txt_files:
                raise FileNotFoundError(
                    "No transcription output was produced by WhisperX. "
                    "Check that '--output_format txt' is supported by your version."
                )

            transcript = txt_files[0].read_text(encoding="utf-8").strip()
            return transcript
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()
