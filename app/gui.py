"""Graphical user interface for the speech-to-text workflow."""
from __future__ import annotations

import datetime as dt
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional

from .audio_recorder import AudioRecorder
from .transcriber import WhisperXTranscriber

LOGGER = logging.getLogger(__name__)


class TranscriptionApp:
    """Tkinter UI coordinating recording and WhisperX transcription."""

    def __init__(
        self,
        root: tk.Tk,
        recorder: AudioRecorder,
        transcriber: WhisperXTranscriber,
    ) -> None:
        self.root = root
        self.recorder = recorder
        self.transcriber = transcriber

        self.is_recording = False
        self.is_transcribing = False
        self._timer_job: Optional[str] = None
        self._recording_started_at: Optional[dt.datetime] = None

        self.language_var = tk.StringVar(value="auto")
        self.translate_var = tk.BooleanVar(value=True)
        self.auto_copy_var = tk.BooleanVar(value=True)
        self.keep_recordings_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready to record")

        self._build_layout()

    # ------------------------------------------------------------------
    # UI construction
    def _build_layout(self) -> None:
        self.root.title("Speech to Text (WhisperX)")
        self.root.geometry("640x480")

        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)

        controls = ttk.Frame(main)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Input language (auto for detection):").grid(
            row=0, column=0, sticky="w"
        )
        language_entry = ttk.Entry(controls, textvariable=self.language_var)
        language_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        options = ttk.Frame(main)
        options.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        options.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            options,
            text="Translate result to English",
            variable=self.translate_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            options,
            text="Copy transcript to clipboard",
            variable=self.auto_copy_var,
        ).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(
            options,
            text="Keep recorded WAV files",
            variable=self.keep_recordings_var,
        ).grid(row=2, column=0, sticky="w")

        button_row = ttk.Frame(main)
        button_row.grid(row=2, column=0, pady=(12, 8))
        self.start_button = ttk.Button(
            button_row, text="🎙️ Start recording", command=self.start_recording
        )
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(
            button_row,
            text="⏹️ Stop & transcribe",
            command=self.stop_recording,
            state=tk.DISABLED,
        )
        self.stop_button.grid(row=0, column=1)

        transcript_frame = ttk.LabelFrame(main, text="Transcript")
        transcript_frame.grid(row=3, column=0, sticky="nsew")
        main.rowconfigure(3, weight=1)

        self.transcript_text = tk.Text(
            transcript_frame,
            wrap="word",
            state=tk.DISABLED,
            font=("Segoe UI", 11),
        )
        scrollbar = ttk.Scrollbar(
            transcript_frame, orient=tk.VERTICAL, command=self.transcript_text.yview
        )
        self.transcript_text.configure(yscrollcommand=scrollbar.set)
        self.transcript_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)

        copy_button = ttk.Button(
            main, text="Copy transcript", command=self.copy_transcript_to_clipboard
        )
        copy_button.grid(row=4, column=0, sticky="e", pady=(8, 0))

        status_bar = ttk.Label(main, textvariable=self.status_var, anchor="w")
        status_bar.grid(row=5, column=0, sticky="ew", pady=(12, 0))

    # ------------------------------------------------------------------
    # Recording handling
    def start_recording(self) -> None:
        if self.is_transcribing:
            messagebox.showwarning(
                "Transcription in progress", "Please wait for the current job to finish."
            )
            return
        if self.is_recording:
            return

        recordings_dir = Path.home() / "Documents" / "SpeechRecordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        audio_path = recordings_dir / f"recording-{timestamp}.wav"

        try:
            self.recorder.start(audio_path)
        except Exception as exc:  # pragma: no cover - hardware dependent
            LOGGER.exception("Failed to start recording")
            messagebox.showerror("Recording error", str(exc))
            return

        self.is_recording = True
        self._recording_started_at = dt.datetime.now()
        self.status_var.set("Recording… Press stop when finished.")
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self._schedule_duration_update()

    def stop_recording(self) -> None:
        if not self.is_recording:
            return

        self.stop_button.configure(state=tk.DISABLED)
        self.status_var.set("Finalizing recording…")
        self.is_recording = False
        if self._timer_job:
            self.root.after_cancel(self._timer_job)
            self._timer_job = None

        try:
            audio_path = self.recorder.stop()
        except Exception as exc:  # pragma: no cover - hardware dependent
            LOGGER.exception("Failed to stop recording")
            messagebox.showerror("Recording error", str(exc))
            self.start_button.configure(state=tk.NORMAL)
            self.status_var.set("Ready to record")
            return

        if audio_path is None:
            self.start_button.configure(state=tk.NORMAL)
            self.status_var.set("Ready to record")
            return

        self.status_var.set("Running WhisperX transcription…")
        self.is_transcribing = True
        thread = threading.Thread(
            target=self._transcribe_thread,
            args=(audio_path,),
            daemon=True,
        )
        thread.start()

    def _schedule_duration_update(self) -> None:
        if not self.is_recording or not self._recording_started_at:
            return
        elapsed = dt.datetime.now() - self._recording_started_at
        seconds = int(elapsed.total_seconds())
        self.status_var.set(f"Recording… {seconds}s")
        self._timer_job = self.root.after(500, self._schedule_duration_update)

    # ------------------------------------------------------------------
    # Transcription handling
    def _transcribe_thread(self, audio_path: Path) -> None:
        language_raw = (self.language_var.get() or "auto").strip()
        language = None if language_raw.lower() in {"", "auto", "automatic"} else language_raw
        translate = bool(self.translate_var.get())

        try:
            transcript = self.transcriber.transcribe(
                audio_path,
                language=language,
                translate=translate,
            )
        except Exception as exc:  # pragma: no cover - depends on WhisperX
            LOGGER.exception("Transcription failed")
            self.root.after(0, self._on_transcription_error, str(exc))
        else:
            self.root.after(0, self._on_transcription_success, transcript)
        finally:
            if not self.keep_recordings_var.get():
                try:
                    audio_path.unlink()
                except FileNotFoundError:
                    pass
                except Exception:  # pragma: no cover - disk permissions
                    LOGGER.warning("Failed to delete temporary recording %s", audio_path)
            self.is_transcribing = False
            self.root.after(0, self._reset_buttons)

    def _on_transcription_success(self, transcript: str) -> None:
        self._set_transcript_text(transcript)
        if self.auto_copy_var.get():
            self._copy_to_clipboard(transcript)
        self.status_var.set("Transcription complete. Text copied to clipboard.")

    def _on_transcription_error(self, message: str) -> None:
        messagebox.showerror("Transcription error", message)
        self.status_var.set("Transcription failed. See logs for details.")

    def _reset_buttons(self) -> None:
        if not self.is_recording:
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)

    def _set_transcript_text(self, transcript: str) -> None:
        self.transcript_text.configure(state=tk.NORMAL)
        self.transcript_text.delete("1.0", tk.END)
        self.transcript_text.insert(tk.END, transcript)
        self.transcript_text.configure(state=tk.DISABLED)

    def copy_transcript_to_clipboard(self) -> None:
        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            messagebox.showinfo("Nothing to copy", "No transcript available yet.")
            return
        self._copy_to_clipboard(transcript)
        self.status_var.set("Transcript copied to clipboard.")

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception as exc:  # pragma: no cover - OS dependent
            LOGGER.exception("Failed to access clipboard")
            messagebox.showwarning(
                "Clipboard error",
                f"Unable to copy transcript to the clipboard.\n{exc}",
            )


def run_app(transcriber: WhisperXTranscriber) -> None:
    """Create the Tkinter root window and run the GUI loop."""
    root = tk.Tk()
    recorder = AudioRecorder()
    TranscriptionApp(root, recorder, transcriber)
    root.mainloop()
