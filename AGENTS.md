# AGENTS.md

This document provides context, architectural guidelines, and workflow conventions for AI coding agents working on the **RasAI** repository.

---

## 1. Project Overview

**RasAI** is a Python-based Indian Classical & Cinematic Symphonic music generator that transforms song lyrics into a fully orchestrated, beat-synchronized stereo MP3 recording (`44.1 kHz`, `320 kbps`) using pure digital signal processing (NumPy & SciPy) and poetic sentiment analysis (`TextBlob`).

### Key Files

- `lyrics_to_music.py`: Primary standalone CLI script and importable Python module. Organized into 12 sequential pipeline sections:
  1. **Shruti (Just Intonation) 3-Octave Tuning System** (`TONIC_FREQUENCIES`, `SHRUTI_RATIOS`, `build_frequency_map`)
  2. **Expanded Raga & Navarasa Definitions** (`RAGAS` dictionary covering 10 Ragas)
  3. **Song Structure Parser** (`parse_sections`, preserving poetic line breaks and meter)
  4. **Navarasa Poetic Sentiment & Raga Selection Engine** (`LEXICON`, `analyze_sentiment`)
  5. **Prosody, Syllables & Beat-Locked Melodic Sequence Builder** (`NoteEvent`, `lyrics_to_notes`)
  6. **Expressive Continuous-Phase Lead & Instrument Synthesis Engine** (`synth_bansuri_continuous`, `synth_sitar_continuous`, `synth_sarangi_continuous`, `synth_swarmandal_gliss`, `render_expressive_melody`)
  7. **Tanpura Drone, Symphonic Pad & Alap Generator** (`tanpura_drone_track`, `symphonic_pad_section`, `generate_alap_intro`)
  8. **Physical-Modeling Tabla & Tala Engine** (`_build_tabla_bols`, `TALA_PATTERNS`, `tabla_track`)
  9. **Concert Hall Stereo Reverb & Studio Mastering Chain** (`apply_concert_hall_reverb`, `master_stereo_bus`)
  10. **MP3 & WAV Export Engine** (`export_audio_to_mp3` with `lameenc` and `ffmpeg` fallback)
  11. **Main Pipeline** (`song_to_music`, `_print_score_table`)
  12. **Default Demo Song & CLI** (`resolve_input_lyrics`, `build_arg_parser`, `main`)
- `lyrics_to_music.ipynb`: Companion Jupyter / Colab notebook for interactive execution.
- `sample_lyrics.txt`: Sample lyrics file with `[Verse 1]`, `[Chorus]`, and `[Bridge]` tags.
- `LICENSE`: GNU General Public License v3.0 (GPL-3.0).

---

## 2. Environment & Common Commands

### Dependencies

- Required: `numpy`, `scipy`, `textblob`
- MP3 encoding: `lameenc` (Python package) or `ffmpeg` (system binary)
- Optional UI / Notebook: `rich`, `ipython`

### Running & Testing

```bash
# Quick CLI syntax and help verification
python3 lyrics_to_music.py --help

# Run with the sample lyrics file
python3 lyrics_to_music.py sample_lyrics.txt -o output_music.mp3

# Run built-in demo with explicit Raga, Tala, and Tonic
python3 lyrics_to_music.py --demo --raga Yaman --tala Teental --tonic C# -o test_output.mp3
```

---

## 3. Musical & DSP Conventions

When modifying or extending the synthesis or composition engines, adhere to the following domain rules:

1. **Swara & Octave Notation**:
   - Lower octave (*Mandra Saptak*): prefixed with a dot, e.g., `.Sa`, `.re`, `.Ni`.
   - Middle octave (*Madhya Saptak*): bare swara name, e.g., `Sa`, `re`, `Re`, `ga`, `Ga`, `Ma`, `ma`, `Pa`, `dha`, `Dha`, `ni`, `Ni`.
   - Upper octave (*Taar Saptak*): suffixed with an apostrophe, e.g., `Sa'`, `Re'`, `Pa'`.
   - Lowercase vowels (`re`, `ga`, `dha`, `ni`) denote *Komal* (flat) swaras; lowercase `ma` denotes *Tivra Madhyam* (sharp fourth); uppercase denotes *Shuddha* (natural) swaras.
2. **Raga Grammar Compliance**:
   - Every Raga in `RAGAS` must define `rasa`, `mood`, `notes`, `aaroha`, `avaroha`, `vadi`, `samvadi`, `andolan`, `drone`, `tempo`, `default_tala`, and `pakad`.
   - Ensure all notes referenced in `aaroha`, `avaroha`, `vadi`, `samvadi`, `andolan`, `drone`, and `pakad` exist in `FREQUENCIES` (via `build_frequency_map`).
3. **Click-Free Continuous-Phase Synthesis**:
   - Avoid concatenating discontinuous sine waves per note. Always compute instantaneous frequency trajectories `f(t)` and integrate phase continuously via `2 * np.pi * np.cumsum(f_inst) / sr` so *Meend* (glides), *Kan* (grace notes), and *Andolan* (oscillations) remain phase-coherent.
4. **Stereo Signal Flow & Headroom**:
   - Internal audio buses use `float64` stereo arrays `(left, right)` at `SAMPLE_RATE = 44100`.
   - Always pass final mixes through `master_stereo_bus` to remove DC offset, apply gentle saturation, and normalize peak levels safely (`~0.94` full scale) before 16-bit PCM quantization.

---

## 4. Coding Guidelines for Agents

- **VENV**: use the ../utmtvenv folder for python imports and runs.
- **Preserve Backward Compatibility**: Keep legacy helper functions (`lyrics_to_notes` tuple unpacking behavior, `render_melody`, `tanpura_drone`, `tabla_track_mono`) working so older notebook cells or external callers do not break.
- **Deterministic Synthesis**: Use seeded `np.random.default_rng(...)` (or deterministic hashes of lyrics/note events) so identical inputs produce reproducible musical compositions and audio outputs.
- **Graceful Fallbacks**:
  - If `rich` is unavailable, fall back cleanly to standard `print()` output.
  - If `lameenc` is unavailable, fall back to `ffmpeg`, and if neither is present, save a `.wav` file with a clear warning rather than crashing.
- **Documentation & Comments**: Maintain existing docstrings and section headers. Update `README.md` if CLI flags, supported Ragas, or dependencies change.
- **License Compliance**: This project is distributed under the **GNU General Public License v3.0 (GPL-3.0)**. Ensure any added code or third-party snippets are compatible with GPL-3.0.

---

## 5. Security, Privacy & Operational Guardrails

AI agents operating in this repository MUST strictly follow these operational boundaries:

- **No Git Commands Without Explicit Approval**: Do **not** run any `git` commands (including `git status`, `git diff`, `git log`, `git add`, `git commit`, `git push`, `git pull`, `git checkout`, `git reset`, `git remote`, etc.) unless specifically requested and approved by the user.
- **Strict Workspace Directory Boundary**: Do **not** read, list, search, or modify any files or directories in parent directories (`..`) or anywhere outside the current project root (`/Users/apple/Code/rasai`) unless specifically approved by the user.
- **No Unapproved Package Installations or System Changes**: Do **not** install global or virtual-environment packages (`pip`, `brew`, `apt`, etc.), modify shell profiles (`.zshrc`, `.bashrc`, `.zshenv`), or change system configurations unless explicitly asked.
- **No Unapproved Network or External API Calls**: Do **not** make outbound network requests, download external weights/corpora, or send project data to external endpoints without explicit user approval.
- **No Destructive File Operations**: Do **not** delete files (`rm`), overwrite user-generated audio/lyrics files, or remove existing code sections unless explicitly instructed by the user.
- **Credentials & Environment Privacy**: Never read, print, or log environment variables, SSH keys, `.env` files, or system credentials.
