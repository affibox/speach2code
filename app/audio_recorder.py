"""Audio recording utilities for the speech-to-text application."""
from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Optional

try:
    import sounddevice as sd
    import soundfile as sf
except Exception as exc:  # pragma: no cover - dependency guard
    raise RuntimeError(
        "The 'sounddevice' and 'soundfile' packages are required for audio "
        "recording. Install them with 'pip install sounddevice soundfile'."
    ) from exc

LOGGER = logging.getLogger(__name__)


class AudioRecorder:
    """Record audio to a WAV file using :mod:`sounddevice`."""

    def __init__(self, samplerate: int = 16_000, channels: int = 1) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self._queue: "queue.Queue" = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._recording_flag = threading.Event()
        self._output_file: Optional[sf.SoundFile] = None
        self._output_path: Optional[Path] = None

    def start(self, destination: Path) -> None:
        """Begin recording audio to ``destination``.

        Parameters
        ----------
        destination:
            Path to the WAV file that should receive the recorded audio.
        """
        if self._recording_flag.is_set():
            raise RuntimeError("Recorder is already running")

        LOGGER.debug("Starting audio recording to %s", destination)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        self._queue = queue.Queue()
        self._output_path = destination
        self._output_file = sf.SoundFile(
            destination,
            mode="w",
            samplerate=self.samplerate,
            channels=self.channels,
            subtype="PCM_16",
        )
        self._recording_flag.set()

        def callback(indata, frames, time, status):  # type: ignore[override]
            if status:
                LOGGER.warning("Sounddevice status: %s", status)
            self._queue.put(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            callback=callback,
        )
        self._stream.start()

        self._writer_thread = threading.Thread(
            target=self._writer_loop, name="AudioWriter", daemon=True
        )
        self._writer_thread.start()

    def stop(self) -> Optional[Path]:
        """Stop recording and finalize the WAV file."""
        if not self._recording_flag.is_set():
            LOGGER.debug("Stop called while recorder inactive")
            return None

        LOGGER.debug("Stopping audio recording")
        self._recording_flag.clear()

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self._writer_thread is not None:
            self._writer_thread.join(timeout=5)
            self._writer_thread = None

        if self._output_file is not None:
            self._output_file.close()

        path = self._output_path
        self._output_path = None
        self._output_file = None
        return path

    def _writer_loop(self) -> None:
        assert self._output_file is not None
        while self._recording_flag.is_set() or not self._queue.empty():
            try:
                data = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            self._output_file.write(data)

    def close(self) -> None:
        """Ensure all resources are released."""
        self._recording_flag.clear()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._writer_thread is not None:
            self._writer_thread.join(timeout=1)
            self._writer_thread = None
        if self._output_file is not None:
            self._output_file.close()
            self._output_file = None

    def __del__(self) -> None:  # pragma: no cover - cleanup guard
        try:
            self.close()
        except Exception:
            LOGGER.exception("Error while cleaning up AudioRecorder")
