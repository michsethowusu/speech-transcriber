# Speech Transcriber

A clean, lightweight, **100% offline in-browser audio transcription and verification tool** designed for field speech dataset curation, listening verification, and text correction.

Built specifically for speech transcription projects (such as Option 2 of speech data collection initiatives). No accounts, no volunteer codes, and no server required.

---

## Key Features

- **100% Offline**: Runs completely inside any browser. Zero internet connection required while transcribing.
- **Fast Batch Loading**:
  - Drag and drop audio files (`.wav`, `.mp3`, `.ogg`).
  - Or drop a `.zip` archive containing audio clips and optional `metadata.csv`.
- **Ergonomic Keyboard Shortcuts**:
  - `Tab`: Play / Pause audio without moving your hands off the keyboard.
  - `Shift + Tab`: Rewind 2 seconds to replay unclear words.
  - `Ctrl + Enter` (or `Shift + Enter`): Save current transcript and advance to the next clip!
- **Auto-Persistent Storage**: Transcripts are automatically saved to browser `IndexedDB`. If the browser is refreshed or closed, all typed work is preserved.
- **One-Click CSV Export**: Download the verified `transcripts.csv` manifest at any time with one click.
- **Adjustable Playback Speed**: Listen at 0.75x, 1.0x, or 1.25x speed.

---

## How to Use

1. **Open the Tool**: Open `index.html` directly in your browser or visit [https://michsethowusu.github.io/speech-transcriber/](https://michsethowusu.github.io/speech-transcriber/).
2. **Load Audio Batch**: Drag and drop audio files, a `.zip` package, or click *Load Sample Audio Practice Clips*.
3. **Listen & Transcribe**:
   - Audio auto-plays when each clip loads.
   - Press `Tab` to pause/resume playback.
   - Type or correct the spoken text in the text area.
   - Press `Ctrl + Enter` (or tap *Save & Next →*) to advance to the next clip.
4. **Export Transcripts**: Tap **📄 Export Transcripts (.CSV)** at any time to download the completed spreadsheet.

---

## License

MIT License. Developed for open speech data collection and language preservation.
