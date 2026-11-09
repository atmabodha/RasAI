# RasAI 🎵

**Indian Classical & Cinematic Symphonic Music Generator from Song Lyrics**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://www.python.org/)

**RasAI** converts song lyrics—from a text file, command-line string, piped input, or interactive prompt—into a fully orchestrated, beat-synchronized **Indian Classical & Cinematic Symphonic MP3 recording**. Built entirely with pure Python digital signal processing (NumPy & SciPy), it analyzes the emotional arc (*Navarasa*) and poetic meter of your lyrics to compose, synthesize, mix, and master an expressive multi-instrument piece from scratch without external sample libraries.

---

## ✨ Key Features

1. **3-Octave Just Intonation (22-Shruti Pure Harmonic Ratios)**
   - Tuned to pure harmonic intervals relative to a configurable concert tonic (`Sa`, defaulting to `C#` = 277.18 Hz) across three octaves: *Mandra Saptak* (`.Sa`–`.Ni`), *Madhya Saptak* (`Sa`–`Ni`), and *Taar Saptak* (`Sa'`–`Pa'`).
2. **Navarasa Emotional Sentiment & 10 Authentic Ragas**
   - Combines a curated poetic/emotional lexicon (Joy, Pathos, Yearning, Peace, Majesty, Bittersweet Contrast) with `TextBlob` polarity/subjectivity and song-section awareness to map each section (`[Verse]`, `[Chorus]`, `[Bridge]`) to an authentic Raga with distinct *Aaroha* (ascending scale), *Avaroha* (descending scale), *Vadi* (king note), *Samvadi* (queen note), *Pakad* (signature phrases), and *Andolan* (oscillating swaras).
3. **Prosody, Motif Memory & Melodic Grammar**
   - Preserves poetic line breaks, syllable counts, stress weights, and rhyme endings.
   - Caches the first `[Chorus]` melodic hook (*Asthayi*) and replays it across subsequent choruses with elevated orchestration.
   - Weaves authentic Raga *Pakad* phrases and multi-syllable melismas (*Swara Vistara*) into long vowels and emotional words.
4. **Expressive Continuous-Phase Lead Synthesis**
   - Zero-click continuous phase integration supporting authentic Indian classical ornamentations: **Meend** (smooth sigmoid pitch glides), **Kan Swara** (35 ms pre-note grace notes), delayed **Andolan / Vibrato**, and **Gamak**.
   - Dynamically blends three synthesized lead voices according to section role and Raga mood:
     - **Bansuri**: Concert bamboo flute with harmonic overtones, chiff attack, and warm breath turbulence.
     - **Sitar**: Plucked string with nonlinear **Jawari** bridge buzz and sympathetic **Taraf** string resonance.
     - **Sarangi / Solo Cello**: Bowed vocal-formant lead for poignant *Karuna* / *Viraha* passages and soaring choruses.
5. **Full Cinematic Orchestration & Physical-Modeled Percussion**
   - **Tanpura Drone**: Continuous stereo 4-string cycle (`Pa/Ma – Sa' – Sa' – .Sa`) with parabolic **Jivari** bridge overtone shimmer.
   - **Symphonic String Pad & Swarmandal**: Lush modal string swells (`Sa–Pa–Vadi–Samvadi`) and stereo Indian harp (*Swarmandal*) glissandi at section transitions.
   - **Stereo Tabla & Tala Engine**: Pitched *Bayan* (left channel, with pitch-drop pressure modulation) and tonic-tuned *Dayan* (right channel, tuned to exact `Sa`), accompanied by *Manjira* bell chimes, sub-bass reinforcement, energetic *Lagi* chorus grooves, and a classic 3-fold **Tihai** cadence at the end of every section.
   - **Introductory Alap & Resolving Outro**: Free-rhythm meditative *Alap* introduction and a resolving *Shadja* (`Sa`) chord with *Swarmandal* tail.
6. **Studio-Grade Stereo Mastering**
   - Multi-tap **Concert Hall Stereo Reverb** with pre-delay and air absorption, warm analog `tanh` saturation, mid/side stereo width enhancement, and **44.1 kHz / 320 kbps Stereo MP3** export (via `lameenc` or `ffmpeg`).

---

## 🎼 Supported Ragas & Talas

### Ragas Across the Navarasa

| Raga | Rasa / Emotional Character | Vadi / Samvadi | Drone | Default Tala |
| :--- | :--- | :---: | :---: | :--- |
| **Yaman** | *Shanta / Shringara* — Serene, Hopeful, Luminous Evening | `Ga` / `Ni` | `Pa` | Keherwa |
| **Desh** | *Shringara / Harsha* — Monsoon Romance, Nostalgia, Warmth | `Re` / `Pa` | `Pa` | Keherwa |
| **Bilawal** | *Utsaha / Hasya* — Radiant Morning, Joy, Celebration | `Dha` / `Ga` | `Pa` | Teental |
| **Hamsadhwani** | *Mangala / Utsaha* — Triumph, Sparkling Celebration, Flight | `Sa` / `Pa` | `Pa` | Teental |
| **Charukeshi** | *Viraha / Shringara* — Bittersweet Catharsis, Cinematic Yearning | `Pa` / `Sa` | `Pa` | Keherwa |
| **Bhairav** | *Bhakti / Adbhuta* — Sacred Dawn, Reverence, Timeless Wonder | `dha` / `re` | `Pa` | Keherwa |
| **Shivaranjani** | *Karuna / Viraha* — Poignant Melancholy, Solitude, Longing | `Pa` / `Sa` | `Pa` | Dadra |
| **Bhairavi** | *Karuna / Bhakti* — Deep Soulful Pathos, Transcendence, Finale | `Ma` / `Sa` | `Pa` | Dadra |
| **Darbari** | *Gambhira / Karuna* — Midnight Majesty, Profound Grief, Gravity | `Re` / `Pa` | `Pa` | Keherwa |
| **Malkauns** | *Veera / Adbhuta* — Cosmic Night, Meditative Power, Mystery | `Ma` / `Sa` | `Ma` | Rupak |

### Rhythmic Cycles (Talas)

| Tala | Beats | Theka Structure |
| :--- | :---: | :--- |
| **Keherwa** | 8 beats | `Dha Ge Na Ti \| Na Ka Dhin Na` |
| **Teental** | 16 beats | `Dha Dhin Dhin Dha \| Dha Dhin Dhin Dha \| Dha Tin Tin Ta \| Ta Dhin Dhin Dha` |
| **Dadra** | 6 beats | `Dha Dhin Na \| Dha Tin Na` |
| **Rupak** | 7 beats | `Tin Tin Na \| Dhin Na \| Dhin Na` |

---

## 📂 Repository Structure

- `lyrics_to_music.py` — Standalone CLI application and Python module containing the full sentiment analyzer, melodic composer, DSP synthesizer, orchestrator, and stereo mastering pipeline.
- `lyrics_to_music.ipynb` — Interactive Jupyter / Google Colab notebook version for exploring and listening to generated music inline.
- `sample_lyrics.txt` — Sample multi-section song lyrics (`[Verse 1]`, `[Chorus]`, `[Bridge]`, `[Chorus]`).
- `output_music.mp3` — Sample generated 320 kbps stereo MP3 audio output.
- `LICENSE` — Full text of the GNU General Public License v3.0 (GPL-3.0).

---

## 🛠️ Installation

### Prerequisites

- **Python 3.8+**
- Optional (fallback for MP3 encoding if `lameenc` is not installed): `ffmpeg` installed on your system `PATH`.

### Install Python Dependencies

```bash
pip install numpy scipy textblob lameenc rich
python -m textblob.download_corpora
```

*(Note: `rich` is optional and provides formatted terminal score tables and progress panels; `ipython` is optional for inline audio playback inside Jupyter notebooks.)*

---

## 🚀 Usage

### 1. Generate Music from a Lyrics File

```bash
python lyrics_to_music.py sample_lyrics.txt -o output_music.mp3
```

### 2. Pass Lyrics Directly from the Command Line

```bash
python lyrics_to_music.py "In the stillness of the morning\nI hear the river calling me" -o morning.mp3
```

### 3. Specify Raga, Tala, Concert Tonic (`Sa`), and Tempo (BPM)

```bash
python lyrics_to_music.py -f sample_lyrics.txt -o yaman_song.mp3 --raga Yaman --tala Teental --tonic D --bpm 88
```

### 4. Run the Built-in Demo Song

```bash
python lyrics_to_music.py --demo -o oscar_demo.mp3
```

### 5. Interactive Mode or Piped Standard Input

```bash
# Interactive prompt
python lyrics_to_music.py

# Piped from stdin
cat sample_lyrics.txt | python lyrics_to_music.py -o piped_song.mp3
```

### Command-Line Options

| Option | Default | Description |
| :--- | :---: | :--- |
| `input` | `None` | Positional path to a `.txt` lyrics file or raw lyrics string |
| `-f`, `--file` | `None` | Path to a text file containing the song lyrics |
| `-l`, `--lyrics` | `None` | Raw lyrics text passed directly via command line |
| `-o`, `--output` | `output_music.mp3` | Output MP3 file path |
| `--bpm` | `84` | Base tempo in Beats Per Minute |
| `--tonic` | `C#` | Concert tonic pitch for `Sa` (`C`, `C#`, `D`, `Eb`, `E`, `F`, `F#`, `G`, `Ab`, `A`, `Bb`, `B`) |
| `--raga` | Auto | Force a specific Raga (`Yaman`, `Desh`, `Bilawal`, `Hamsadhwani`, `Charukeshi`, `Bhairav`, `Shivaranjani`, `Bhairavi`, `Darbari`, `Malkauns`) |
| `--tala` | Auto | Force a specific Tala (`Keherwa`, `Teental`, `Dadra`, `Rupak`) |
| `--melody-vol` | `0.82` | Lead melody mix level (`0.0` – `1.0`) |
| `--tabla-vol` | `0.34` | Tabla & percussion mix level (`0.0` – `1.0`) |
| `--drone-vol` | `0.24` | Tanpura drone mix level (`0.0` – `1.0`) |
| `--pad-vol` | `0.30` | Symphonic string pad mix level (`0.0` – `1.0`) |
| `--no-alap` | `False` | Disable the introductory *Alap* before the first section |
| `--wav` | `False` | Also save an uncompressed `.wav` file alongside the `.mp3` |
| `--demo` | `False` | Run immediately using the built-in 4-section song |

### Python API Usage

You can also import and call `song_to_music` directly in Python scripts or notebooks:

```python
from lyrics_to_music import song_to_music

lyrics = """[Verse 1]
In the stillness of the morning
I hear the river calling me

[Chorus]
Oh take me home take me home
Where the mountains meet the sea
"""

output_path = song_to_music(
    raw_lyrics=lyrics,
    output_mp3="my_composition.mp3",
    bpm=84,
    tonic="C#",
    forced_raga=None,   # Auto-selects Raga per section via Navarasa analysis
    forced_tala=None,   # Auto-matches Tala to the selected Raga
    include_alap=True,
    also_save_wav=False,
)
```

---

## 📜 License

This project is released in Git as free and open-source software under the **GNU General Public License v3.0 (GPL-3.0)**.

- You are free to **use, study, share, and modify** this software under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
- Any distributed modifications or derivative works must also be licensed under the **GPL-3.0** and made available with their complete corresponding source code.
- This software is distributed in the hope that it will be useful, **without any warranty**; without even the implied warranty of **merchantability** or **fitness for a particular purpose**.

See the [LICENSE](LICENSE) file in this repository or visit <https://www.gnu.org/licenses/gpl-3.0.html> for the full license text and terms.
