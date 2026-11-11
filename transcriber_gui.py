#!/usr/bin/env python3
"""LEIN Offline Speech Transcriber — Tkinter Desktop GUI.

A lightweight, ergonomic desktop application for audio listening, transcription,
and text correction. Runs 100% offline, handles local audio folders or ZIP batches,
features keyboard-driven playback and text editing, performs length validation with
user override, and auto-saves directly to CSV.
"""

import os
import sys
import time
import zipfile
import csv
import re
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import sounddevice as sd
import soundfile as sf


class SpeechTranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LEIN Speech Transcriber — Offline Transcription Studio")
        self.root.geometry("860x700")
        self.root.minsize(780, 600)

        # State
        self.clips = []  # list of { filename, filepath/bytes, transcript, duration }
        self.current_index = 0
        self.transcripts_map = {}  # filename -> { transcript, status, duration }
        self.is_playing = False
        self.current_audio_data = None
        self.current_sr = 44100
        self.playback_speed = 1.0
        self.pending_override = None
        self.play_loop_count = 0
        self.max_plays = 3
        self.playback_after_id = None
        self.countdown_after_id = None

        # Output Directories
        self.output_dir = Path("transcriptions")
        self.transcripts_file = self.output_dir / "transcripts.csv"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._build_ui()
        self._load_existing_transcripts()
        self._check_local_audio()

    def _build_ui(self):
        self.bg_color = "#F8FAFC"
        self.card_bg = "#FFFFFF"
        self.root.configure(bg=self.bg_color)

        # Header Bar
        top_frame = tk.Frame(self.root, bg=self.card_bg, padx=16, pady=10, relief=tk.SOLID, bd=1)
        top_frame.pack(fill=tk.X, side=tk.TOP)

        brand_lbl = tk.Label(top_frame, text="LEIN Speech Transcriber", font=("Arial", 13, "bold"), bg=self.card_bg)
        brand_lbl.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(top_frame, text="Volunteer Name / ID:", font=("Arial", 10, "bold"), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 4))
        self.volunteer_entry = tk.Entry(top_frame, font=("Arial", 10), width=18)
        self.volunteer_entry.insert(0, "Volunteer_1")
        self.volunteer_entry.pack(side=tk.LEFT, padx=(0, 16))

        self.export_btn = tk.Button(top_frame, text="Export Transcripts (.CSV)", font=("Arial", 10, "bold"),
                                    bg="#0F172A", fg="#FFFFFF", activebackground="#1E293B", activeforeground="#FFF",
                                    padx=12, pady=4, cursor="hand2", command=self.export_csv)
        self.export_btn.pack(side=tk.RIGHT)

        load_btn = tk.Button(top_frame, text="Load Audio Folder / ZIP", font=("Arial", 10),
                             bg="#F1F5F9", relief=tk.GROOVE, padx=10, pady=3,
                             command=self.load_audio_dialog)
        load_btn.pack(side=tk.RIGHT, padx=8)

        # Main Workspace Container
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.transcribe_card = tk.Frame(main_frame, bg=self.card_bg, relief=tk.SOLID, bd=1, padx=24, pady=20)
        self.transcribe_card.pack(fill=tk.BOTH, expand=True)

        # Meta row (Clip name & Progress)
        meta_row = tk.Frame(self.transcribe_card, bg=self.card_bg)
        meta_row.pack(fill=tk.X, pady=(0, 14))

        self.clip_name_lbl = tk.Label(meta_row, text="No Audio Loaded", font=("Courier", 12, "bold"), bg="#EFF6FF", fg="#1D4ED8", padx=8, pady=2)
        self.clip_name_lbl.pack(side=tk.LEFT)

        self.status_badge_lbl = tk.Label(meta_row, text="", font=("Arial", 10, "bold"), bg=self.card_bg)
        self.status_badge_lbl.pack(side=tk.LEFT, padx=12)

        self.progress_lbl = tk.Label(meta_row, text="Clip 0 of 0 | 0 Completed", font=("Arial", 10, "bold"), fg="#64748B", bg=self.card_bg)
        self.progress_lbl.pack(side=tk.RIGHT)

        # Audio Player Bar
        player_box = tk.Frame(self.transcribe_card, bg="#F1F5F9", relief=tk.GROOVE, padx=14, pady=10)
        player_box.pack(fill=tk.X, pady=(0, 14))

        self.play_btn = tk.Button(player_box, text="▶ Play (Tab)", font=("Arial", 10, "bold"),
                                  bg="#0F172A", fg="#FFF", activebackground="#1E293B", activeforeground="#FFF",
                                  padx=12, pady=4, cursor="hand2", command=self.toggle_playback)
        self.play_btn.pack(side=tk.LEFT, padx=(0, 8))

        rewind_btn = tk.Button(player_box, text="↺ -2s (Shift+Tab)", font=("Arial", 9), padx=8, pady=4, command=self.rewind_audio)
        rewind_btn.pack(side=tk.LEFT, padx=(0, 12))

        self.time_lbl = tk.Label(player_box, text="0.0s / 0.0s", font=("Courier", 10, "bold"), bg="#F1F5F9")
        self.time_lbl.pack(side=tk.LEFT, padx=4)

        self.loop_status_lbl = tk.Label(player_box, text="", font=("Arial", 9, "bold"), bg="#F1F5F9", fg="#2563EB")
        self.loop_status_lbl.pack(side=tk.LEFT, padx=12)

        # Speed Selector
        tk.Label(player_box, text="Speed:", font=("Arial", 9, "bold"), bg="#F1F5F9").pack(side=tk.RIGHT, padx=(4, 0))
        self.speed_combo = ttk.Combobox(player_box, state="readonly", values=["0.75x", "1.0x", "1.25x"], width=7)
        self.speed_combo.current(1)
        self.speed_combo.bind("<<ComboboxSelected>>", self.on_speed_change)
        self.speed_combo.pack(side=tk.RIGHT, padx=(0, 8))

        # Warning / Length Override Box
        self.warning_frame = tk.Frame(self.transcribe_card, bg="#FEF3C7", padx=14, pady=10, relief=tk.SOLID, bd=1)
        self.warning_lbl = tk.Label(self.warning_frame, text="", font=("Arial", 9, "bold"), bg="#FEF3C7", fg="#92400E", justify=tk.LEFT)
        self.warning_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.confirm_override_btn = tk.Button(self.warning_frame, text="Save Anyway (Mark for Review)", font=("Arial", 9, "bold"),
                                             bg="#D97706", fg="#FFF", command=self.confirm_override)
        self.confirm_override_btn.pack(side=tk.RIGHT, padx=4)

        # Transcription Text Input
        tk.Label(self.transcribe_card, text="Transcription (Listen & Type / Correct):", font=("Arial", 11, "bold"), bg=self.card_bg).pack(anchor=tk.W, pady=(4, 6))

        self.text_editor = tk.Text(self.transcribe_card, font=("Arial", 13), wrap=tk.WORD, height=6, relief=tk.SOLID, bd=1, padx=10, pady=10)
        self.text_editor.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        # Navigation Bar
        nav_row = tk.Frame(self.transcribe_card, bg=self.card_bg)
        nav_row.pack(fill=tk.X, pady=(0, 10))

        self.prev_btn = tk.Button(nav_row, text="← Previous Clip", font=("Arial", 10, "bold"), padx=14, pady=6, command=self.prev_clip)
        self.prev_btn.pack(side=tk.LEFT)

        self.save_next_btn = tk.Button(nav_row, text="Save & Next → (Ctrl+Enter)", font=("Arial", 11, "bold"),
                                       bg="#0F172A", fg="#FFF", activebackground="#1E293B", activeforeground="#FFF",
                                       padx=18, pady=7, cursor="hand2", command=self.save_and_next)
        self.save_next_btn.pack(side=tk.RIGHT)

        # Shortcuts Footer
        footer_row = tk.Frame(self.transcribe_card, bg=self.card_bg)
        footer_row.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        shortcuts_text = "Shortcuts: Tab = Play/Pause  |  Shift+Tab = Rewind 2s  |  Ctrl+Enter = Save & Next  |  Alt+Left = Prev"
        tk.Label(footer_row, text=shortcuts_text, font=("Arial", 9), fg="#64748B", bg=self.card_bg).pack(side=tk.LEFT)

        # Global Keyboard Bindings
        self.root.bind("<Tab>", lambda e: self._on_tab(e))
        self.root.bind("<Shift-Tab>", lambda e: self._on_shift_tab(e))
        self.root.bind("<Control-Return>", lambda e: self.save_and_next())
        self.root.bind("<Alt-Left>", lambda e: self.prev_clip())

    def _check_local_audio(self):
        sample_dir = Path("sample_audio")
        if sample_dir.exists():
            wavs = list(sample_dir.glob("*.wav"))
            if wavs:
                self._load_from_file_list(wavs)

    def load_audio_dialog(self):
        choice = messagebox.askquestion("Load Audio", "Click 'Yes' to load an Audio Folder, or 'No' to open a .ZIP batch file.")
        if choice == "yes":
            folder = filedialog.askdirectory(title="Select Folder Containing Audio Files")
            if folder:
                wavs = [p for p in Path(folder).glob("**/*") if p.suffix.lower() in [".wav", ".mp3", ".ogg", ".flac"]]
                if not wavs:
                    messagebox.showerror("No Audio", "No audio files (.wav, .mp3) found in selected folder.")
                    return
                self._load_from_file_list(wavs)
        else:
            zip_path = filedialog.askopenfilename(filetypes=[("ZIP Archives", "*.zip")])
            if zip_path:
                self._load_from_zip(Path(zip_path))

    def _load_from_file_list(self, file_paths):
        loaded = []
        for p in file_paths:
            loaded.append({
                "filename": p.name,
                "filepath": str(p),
                "is_zip": False,
                "transcript": ""
            })
        loaded.sort(key=lambda x: x["filename"])
        self.clips = loaded
        self.current_index = 0
        self._show_current_clip()
        self._update_stats()

    def _load_from_zip(self, zip_path):
        import tempfile
        extract_dir = Path(tempfile.mkdtemp(prefix="transcriber_zip_"))
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Check for metadata.csv
        meta_file = next(extract_dir.glob("**/metadata.csv"), None) or next(extract_dir.glob("**/transcripts.csv"), None)
        meta_dict = {}
        if meta_file:
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        fn = r.get("audio_filename") or r.get("filename")
                        txt = r.get("sentence") or r.get("transcript") or r.get("text")
                        if fn and txt:
                            meta_dict[fn] = txt
            except Exception as e:
                print(f"Meta parse error: {e}")

        wavs = [p for p in extract_dir.glob("**/*") if p.suffix.lower() in [".wav", ".mp3", ".ogg", ".flac"]]
        if not wavs:
            messagebox.showerror("ZIP Error", "No audio files found inside the ZIP.")
            return

        loaded = []
        for p in wavs:
            loaded.append({
                "filename": p.name,
                "filepath": str(p),
                "is_zip": True,
                "transcript": meta_dict.get(p.name, "")
            })

        loaded.sort(key=lambda x: x["filename"])
        self.clips = loaded
        self.current_index = 0
        self._show_current_clip()
        self._update_stats()

    def _load_existing_transcripts(self):
        if not self.transcripts_file.exists():
            return
        try:
            with open(self.transcripts_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    fn = r.get("audio_filename")
                    if fn:
                        self.transcripts_map[fn] = {
                            "transcript": r.get("transcript", ""),
                            "status": r.get("status", "completed"),
                            "duration": r.get("duration_seconds", "0.0")
                        }
            self._update_stats()
        except Exception as e:
            print(f"Error loading transcripts: {e}")

    def _show_current_clip(self, autoplay=False):
        if not self.clips:
            return
        self._stop_playback()
        self.warning_frame.pack_forget()
        self.pending_override = None

        cur = self.clips[self.current_index]
        self.clip_name_lbl.configure(text=cur["filename"])
        self.progress_lbl.configure(text=f"Clip {self.current_index + 1} of {len(self.clips)} | {len(self.transcripts_map)} Completed")

        # Load audio into memory
        try:
            data, sr = sf.read(cur["filepath"])
            if data.ndim > 1:
                data = data[:, 0]
            self.current_audio_data = data
            self.current_sr = sr
            dur_sec = len(data) / sr
            self.time_lbl.configure(text=f"0.0s / {dur_sec:.1f}s")
        except Exception as e:
            self.current_audio_data = None
            self.time_lbl.configure(text="Error loading audio")

        # Set transcript text
        saved = self.transcripts_map.get(cur["filename"])
        text_to_show = saved["transcript"] if saved else cur["transcript"]
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", text_to_show)

        if saved:
            status = saved.get("status", "completed")
            if status.startswith("needs_review"):
                self.status_badge_lbl.configure(text=f"⚠️ {status}", fg="#92400E")
            else:
                self.status_badge_lbl.configure(text="✓ Transcribed", fg="#166534")
        else:
            self.status_badge_lbl.configure(text="")

        # Focus text editor
        self.text_editor.focus_set()

        # Auto-play audio clip only when advancing to next
        if autoplay:
            self.toggle_playback()

    def _update_stats(self):
        count = len(self.transcripts_map)
        total = len(self.clips)
        self.progress_lbl.configure(text=f"Clip {self.current_index + 1} of {total} | {count} Completed")
        self.export_btn.configure(state=tk.NORMAL if count > 0 else tk.DISABLED)

    # -------------------------------------------------------------
    # PLAYBACK ENGINE (3-REPEAT WITH 3-SECOND COUNTDOWN BETWEEN PLAYS)
    # -------------------------------------------------------------

    def _stop_playback(self):
        try:
            sd.stop()
        except Exception:
            pass
        if self.playback_after_id:
            try:
                self.root.after_cancel(self.playback_after_id)
            except Exception:
                pass
            self.playback_after_id = None
        if self.countdown_after_id:
            try:
                self.root.after_cancel(self.countdown_after_id)
            except Exception:
                pass
            self.countdown_after_id = None
        self.is_playing = False
        self.play_loop_count = 0
        self.play_btn.configure(text="▶ Play (Tab)")
        self.loop_status_lbl.configure(text="")

    def toggle_playback(self, max_plays=3):
        if self.current_audio_data is None:
            return
        if self.is_playing:
            self._stop_playback()
        else:
            self.is_playing = True
            self.play_loop_count = 0
            self.max_plays = max_plays
            self.play_btn.configure(text="⏸ Pause (Tab)")
            self._play_next_iteration()

    def _play_next_iteration(self):
        if not self.is_playing or self.current_audio_data is None:
            return
        self.play_loop_count += 1
        self.loop_status_lbl.configure(
            text=f"🔊 Playing take {self.play_loop_count} of {self.max_plays}...",
            fg="#1D4ED8"
        )
        target_sr = int(self.current_sr * self.playback_speed)
        try:
            sd.play(self.current_audio_data, target_sr)
        except Exception as e:
            self._stop_playback()
            return

        dur_ms = int((len(self.current_audio_data) / target_sr) * 1000) + 80
        self.playback_after_id = self.root.after(dur_ms, self._on_single_play_done)

    def _on_single_play_done(self):
        try:
            sd.stop()
        except Exception:
            pass
        self.playback_after_id = None

        if not self.is_playing:
            return

        if self.play_loop_count < self.max_plays:
            # Start the 3-second countdown before playing again
            self._start_countdown(3)
        else:
            # Finished all 3 repetitions
            self._stop_playback()

    def _start_countdown(self, seconds_left):
        if not self.is_playing:
            return
        if seconds_left > 0:
            next_take = self.play_loop_count + 1
            self.loop_status_lbl.configure(
                text=f"⏸ Playing again in {seconds_left}s... (Take {next_take} of {self.max_plays})",
                fg="#D97706"
            )
            self.countdown_after_id = self.root.after(1000, lambda: self._start_countdown(seconds_left - 1))
        else:
            self.countdown_after_id = None
            self._play_next_iteration()

    def rewind_audio(self):
        self._stop_playback()
        self.toggle_playback(max_plays=3)

    def on_speed_change(self, event=None):
        val = self.speed_combo.get().replace("x", "")
        try:
            self.playback_speed = float(val)
        except Exception:
            self.playback_speed = 1.0

    def _on_tab(self, event):
        self.toggle_playback()
        return "break"

    def _on_shift_tab(self, event):
        self.rewind_audio()
        return "break"

    # -------------------------------------------------------------
    # VALIDATION, OVERRIDE & SAVING
    # -------------------------------------------------------------

    def save_and_next(self):
        if not self.clips:
            return
        text = self.text_editor.get("1.0", tk.END).strip()
        cur = self.clips[self.current_index]

        if not text:
            messagebox.showinfo("Empty Transcript", "Please type or verify the transcription before advancing.")
            return

        words = [w for w in re.split(r'\s+', text) if w]
        dur_sec = len(self.current_audio_data) / self.current_sr if self.current_audio_data is not None else 0

        status = "completed"
        warn_msg = ""

        # Too short validation
        if dur_sec > 2.5 and (len(words) < 3 or len(text) < 8):
            status = "needs_review_too_short"
            warn_msg = f"Transcript appears unusually short ({len(words)} words for {dur_sec:.1f}s audio). Did you transcribe all spoken words?"
        # Too long validation
        elif (dur_sec > 0 and len(words) / dur_sec > 4.5) or len(words) > 65:
            status = "needs_review_too_long"
            warn_msg = f"Transcript appears unusually long ({len(words)} words for {dur_sec:.1f}s audio). Please verify text matches audio."

        if status != "completed" and self.pending_override != cur["filename"]:
            # Trigger warning and allow override
            self.pending_override = cur["filename"]
            self.warning_lbl.configure(text=f"⚠️ {warn_msg}")
            self.warning_frame.pack(fill=tk.X, pady=(0, 10), before=self.text_editor)
            return

        # Normal pass or overridden: Commit!
        self._commit_transcript(cur["filename"], text, status, dur_sec)
        self.warning_frame.pack_forget()
        self.pending_override = None

        if self.current_index < len(self.clips) - 1:
            self.current_index += 1
            self._show_current_clip(autoplay=True)
        else:
            messagebox.showinfo("Completed", "You have reached the end of the loaded audio batch!")

    def confirm_override(self):
        text = self.text_editor.get("1.0", tk.END).strip()
        cur = self.clips[self.current_index]
        dur_sec = len(self.current_audio_data) / self.current_sr if self.current_audio_data is not None else 0
        words = [w for w in re.split(r'\s+', text) if w]

        flag = "needs_review_too_short" if len(words) < 3 else "needs_review_too_long"
        self._commit_transcript(cur["filename"], text, flag, dur_sec)
        self.warning_frame.pack_forget()
        self.pending_override = None

        if self.current_index < len(self.clips) - 1:
            self.current_index += 1
            self._show_current_clip(autoplay=True)
        else:
            messagebox.showinfo("Completed", "You have reached the end of the loaded audio batch!")

    def _commit_transcript(self, filename, text, status, duration_sec):
        record = {
            "audio_filename": filename,
            "transcript": text,
            "status": status,
            "duration_seconds": f"{duration_sec:.2f}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "volunteer": self.volunteer_entry.get().strip() or "volunteer"
        }
        self.transcripts_map[filename] = record
        self._append_transcript_record(record)
        self._update_stats()

    def _append_transcript_record(self, record):
        file_exists = self.transcripts_file.exists()
        fieldnames = ["audio_filename", "transcript", "status", "duration_seconds", "timestamp", "volunteer"]

        rows = {}
        if file_exists:
            with open(self.transcripts_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows[r["audio_filename"]] = r

        rows[record["audio_filename"]] = record

        with open(self.transcripts_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows.values():
                writer.writerow(r)

    def prev_clip(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._show_current_clip()

    # -------------------------------------------------------------
    # EXPORT CSV
    # -------------------------------------------------------------

    def export_csv(self):
        if not self.transcripts_map:
            messagebox.showinfo("Export", "No transcripts recorded to export yet.")
            return

        volunteer = re.sub(r'[^a-zA-Z0-9_-]', '_', self.volunteer_entry.get().strip() or "volunteer")
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        default_name = f"transcripts_{volunteer}_{date_str}_{len(self.transcripts_map)}clips.csv"

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Spreadsheet", "*.csv")]
        )
        if not save_path:
            return

        try:
            fieldnames = ["audio_filename", "transcript", "status", "duration_seconds", "timestamp", "volunteer"]
            with open(save_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for rec in self.transcripts_map.values():
                    writer.writerow(rec)

            messagebox.showinfo("Export Successful", f"Saved {len(self.transcripts_map)} verified transcripts to:\n{save_path}")

        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = SpeechTranscriberApp(root)
    root.mainloop()
