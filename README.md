# Speech to Code – WhisperX Desktop Helper

A small Tkinter desktop app that lets you record speech from your microphone, send
it through [WhisperX](https://github.com/m-bain/whisperX) inside your existing
Conda environment, and receive an English transcript ready to paste into your
coding tools.

## Features

- 🎙️ One-click recording with live duration indicator.
- 🔁 Automatic WhisperX transcription with the **Translate to English** task.
- 📋 Automatically copies the result to the clipboard so you can press `Ctrl+V`
  wherever your cursor is focused.
- 🌐 Works regardless of the spoken language (default is automatic detection).
- 💾 Optionally keep the recorded WAV files for later reference.

## Requirements

1. Activate your Conda environment that already contains WhisperX:

   ```bash
   conda activate whisper-fast
   ```

2. Install the small Python dependencies needed for audio capture:

   ```bash
   pip install -r requirements.txt
   ```

   (If you prefer to use `pip install sounddevice soundfile` manually, that works
   too.)

3. Make sure WhisperX is available on the command line. You should already be
   able to run a command such as:

   ```bash
   whisperx --device cuda --model large-v3 --language Spanish --output_format txt
   ```

   The app reuses the same executable, so any flags supported by your local
   installation will continue to work.

## Usage

1. While still inside the activated Conda environment, start the desktop helper:

   ```bash
   python main.py --device cuda --model large-v3
   ```

   Optional CLI flags:

   - `--whisperx-cmd`: alternate executable path/name (defaults to `whisperx`).
   - `--compute-type`: forward a compute type such as `float16`.
   - `--extra-args`: supply any additional WhisperX arguments. Everything after
     this flag is passed through unchanged (e.g.
     `python main.py --extra-args --align_model small`).

2. In the window that opens:

   - Press **🎙️ Start recording** to begin capturing audio.
   - Speak in any language; leave the *Input language* field set to `auto` for
     detection, or type something like `Spanish` to lock the language.
   - Press **⏹️ Stop & transcribe** when finished. WhisperX will run with the
     translate task so the output is English regardless of the spoken language.
   - The transcript appears in the lower panel and is copied to the clipboard by
     default so you can paste it wherever the cursor currently is.

3. Use the checkboxes to toggle automatic clipboard copying or to keep/delete the
   raw WAV recordings (they are stored under `~/Documents/SpeechRecordings`).

## Troubleshooting

- **No audio devices found** – make sure the `sounddevice` package can access a
  working input device. Installing the latest audio drivers on Windows often
  resolves this.
- **WhisperX executable not found** – confirm you launched the app from inside
  the `whisper-fast` environment where WhisperX is installed. You can also point
  to a specific executable with `--whisperx-cmd "C:/path/to/whisperx.exe"`.
- **CUDA/compute issues** – use `--device cpu` or adjust `--compute-type` if your
  GPU drivers are not detected.

## Development

The code is organized into three small modules:

- `app/audio_recorder.py`: microphone recording utilities using `sounddevice`.
- `app/transcriber.py`: lightweight wrapper around the WhisperX CLI.
- `app/gui.py`: Tkinter interface wiring the pieces together.

Run `python -m compileall .` after making changes to catch syntax errors.
