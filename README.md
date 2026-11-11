# Speech Transcriber (Python Desktop GUI)

A clean, native **Python Tkinter desktop application** for offline audio listening, speech transcription, and text verification.

Designed for speech data collection projects (Option 2). Operates 100% offline, handles local audio directories or `.zip` archives, and provides an ergonomic keyboard-driven transcription workflow.

---

## Quick Start

### 1. Requirements
Make sure Python 3 is installed along with the required audio packages:
```bash
pip install sounddevice soundfile numpy
```

### 2. Launch the App
- **Windows**: Double-click `run.bat` (or run `python transcriber_gui.py`)
- **Linux / Mac**: Double-click `run.sh` (or run `python3 transcriber_gui.py`)

---

## Features

- **Batch Audio Loader**: Load a folder of audio files (`.wav`, `.mp3`, `.ogg`) or open a `.zip` archive directly.
- **Ergonomic Keyboard Workflow**:
  - `Tab`: Play / Pause audio without taking hands off the keyboard.
  - `Shift + Tab`: Rewind 2 seconds to replay unclear words.
  - `Ctrl + Enter`: Save current transcript and advance to the next clip!
  - `Alt + Left`: Return to previous clip.
  - Playback speed selector ($0.75\times$, $1.0\times$, $1.25\times$).
- **Length Quality Check**: Detects if a transcript is unusually short ($<3$ words) or too long relative to the audio duration, with a *"Save Anyway (Mark for Review)"* override option.
- **Direct CSV Auto-Save**: Writes transcripts directly to `transcriptions/transcripts.csv` tracking `completed` vs. `needs_review_*` statuses.
- **One-Click CSV Export**: Exports a clean, finalized spreadsheet with verified transcripts.

---

## License
MIT License.
