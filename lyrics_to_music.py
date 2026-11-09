#!/usr/bin/env python3
"""
RasAI — Oscar-Edition Indian Classical & Cinematic Symphonic Music Generator
============================================================================
Converts song lyrics (from a text file, command-line argument, or interactive
stdin) into a fully orchestrated, beat-synchronized Indian Classical & Cinematic
Symphonic MP3 recording.

Key Musical & DSP Innovations over the original notebook:
  1. 3-Octave Just Intonation (22-Shruti Pure Harmonic Ratios) across Mandra
     (.Sa-.Ni), Madhya (Sa-Ni), and Taar (Sa'-Pa') Saptaks.
  2. 10 Authentic Ragas across the Navarasa (9 Emotional States) with distinct
     Aaroha (ascending), Avaroha (descending), Vadi (king note), Samvadi (queen
     note), Pakad (signature melodic motifs), and Andolan (oscillating swaras).
  3. Deep Poetic & Navarasa Sentiment Analyzer: Combines a curated poetic/emotional
     lexicon (Joy, Pathos, Yearning, Peace, Majesty, Bittersweet Contrast) with
     TextBlob polarity/subjectivity and structural arc awareness.
  4. Motif Memory & Melodic Grammar: Preserves line breaks, poetic meter, and
     rhyme phrasing; caches and replays the Chorus melodic hook (Asthayi) across
     repeated choruses while elevating orchestration; weaves Pakad phrases and
     multi-syllable melismas (Swara Vistara) into the melody.
  5. Continuous-Phase Expressive Synthesis: True Meend (sigmoid pitch glides),
     Kan Swara (grace notes), delayed Andolan/Vibrato, and Gamak across three
     blended lead instruments:
       - Bansuri (concert bamboo flute with breath turbulence & chiff)
       - Sitar (plucked string with nonlinear Jawari bridge buzz & Taraf strings)
       - Sarangi / Solo Cello (bowed vocal-formant lead for deep emotional pathos)
  6. Full Cinematic Orchestration:
       - Stereo Tanpura Drone with Jivari harmonic shimmer
       - Lush Symphonic String Pad swells (Sa-Pa-Vadi-Samvadi modal voicings)
       - Swarmandal (Indian harp) stereo glissandi at section transitions
       - Beat-locked Stereo Tabla (pitched Bayan + tonic-tuned Dayan) playing
         authentic Talas (Keherwa, Teental, Dadra, Rupak) with Lagi grooves,
         Manjira chimes, cinematic sub-bass, and rhythmic Tihai cadences.
       - Atmospheric Alap Intro & Resolving Tihai Outro.
  7. Studio-Grade Stereo Mastering: Concert Hall Stereo Reverb, warm analog
     saturation, stereo imaging, and 320 kbps MP3 export via lameenc / ffmpeg.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import signal
from textblob import TextBlob

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


# ==============================================================================
# 1. SHRUTI (JUST INTONATION) 3-OCTAVE TUNING SYSTEM
# ==============================================================================

TONIC_FREQUENCIES: Dict[str, float] = {
    "C":  261.63,
    "C#": 277.18,
    "Db": 277.18,
    "D":  293.66,
    "D#": 311.13,
    "Eb": 311.13,
    "E":  329.63,
    "F":  349.23,
    "F#": 369.99,
    "Gb": 369.99,
    "G":  392.00,
    "G#": 415.30,
    "Ab": 415.30,
    "A":  440.00,
    "A#": 466.16,
    "Bb": 466.16,
    "B":  493.88,
}

# Pure harmonic Shruti ratios relative to Shadja (Sa = 1/1)
SHRUTI_RATIOS: Dict[str, float] = {
    "Sa":  1.000000,          # 1/1   Shadja
    "re":  16.0 / 15.0,       # 16/15 Komal Rishabh
    "Re":  9.0 / 8.0,         # 9/8   Shuddha Rishabh
    "ga":  6.0 / 5.0,         # 6/5   Komal Gandhar
    "Ga":  5.0 / 4.0,         # 5/4   Shuddha Gandhar
    "Ma":  4.0 / 3.0,         # 4/3   Shuddha Madhyam
    "ma":  45.0 / 32.0,       # 45/32 Tivra Madhyam
    "Pa":  3.0 / 2.0,         # 3/2   Pancham
    "dha": 8.0 / 5.0,         # 8/5   Komal Dhaivat
    "Dha": 5.0 / 3.0,         # 5/3   Shuddha Dhaivat
    "ni":  9.0 / 5.0,         # 9/5   Komal Nishad
    "Ni":  15.0 / 8.0,        # 15/8  Shuddha Nishad
}


def build_frequency_map(tonic_hz: float = 261.63) -> Dict[str, float]:
    """Build 3-octave Just Intonation frequency dictionary (.Sa to Pa')."""
    freqs: Dict[str, float] = {}
    for swara, ratio in SHRUTI_RATIOS.items():
        # Mandra Saptak (lower octave: .Sa, .Re, ...)
        freqs[f".{swara}"] = tonic_hz * ratio * 0.5
        # Madhya Saptak (middle octave: Sa, Re, ...)
        freqs[swara] = tonic_hz * ratio
        # Taar Saptak (upper octave: Sa', Re', ...)
        freqs[f"{swara}'"] = tonic_hz * ratio * 2.0
    # Legacy alias from original notebook
    freqs["Sa2"] = freqs["Sa'"]
    return freqs


SAMPLE_RATE = 44100
FREQUENCIES = build_frequency_map(261.63)


# ==============================================================================
# 2. EXPANDED RAGA & NAVARASA DEFINITIONS
# ==============================================================================

RAGAS: Dict[str, Dict] = {
    "Yaman": {
        "rasa": "Shanta / Shringara (Serene, Hopeful, Luminous Evening)",
        "mood": "peaceful",
        "notes": [".Ni", "Sa", "Re", "Ga", "ma", "Pa", "Dha", "Ni", "Sa'", "Re'", "Ga'"],
        "aaroha": [".Ni", "Re", "Ga", "ma", "Dha", "Ni", "Sa'"],
        "avaroha": ["Sa'", "Ni", "Dha", "Pa", "ma", "Ga", "Re", "Sa"],
        "vadi": "Ga",
        "samvadi": "Ni",
        "andolan": ["Ga", "Ni"],
        "drone": "Pa",
        "tempo": 0.92,
        "default_tala": "Keherwa",
        "pakad": [
            [".Ni", "Re", "Ga", "ma", "Pa"],
            ["ma", "Dha", "Ni", "Sa'", "Ni", "Dha", "Pa"],
            ["Pa", "ma", "Ga", "Re", "Sa"],
        ],
    },
    "Desh": {
        "rasa": "Shringara / Harsha (Monsoon Romance, Nostalgia, Warmth)",
        "mood": "warm_joy",
        "notes": [".Ni", "Sa", "Re", "Ga", "Ma", "Pa", "Dha", "ni", "Ni", "Sa'", "Re'"],
        "aaroha": [".Ni", "Sa", "Re", "Ma", "Pa", "Ni", "Sa'"],
        "avaroha": ["Sa'", "ni", "Dha", "Pa", "Ma", "Ga", "Re", "Ga", ".Ni", "Sa"],
        "vadi": "Re",
        "samvadi": "Pa",
        "andolan": ["ni", "Ga"],
        "drone": "Pa",
        "tempo": 0.96,
        "default_tala": "Keherwa",
        "pakad": [
            ["Re", "Ma", "Pa", "ni", "Dha", "Pa"],
            ["Ma", "Ga", "Re", ".Ni", "Sa"],
            ["Re", "Ma", "Pa", "Ni", "Sa'"],
        ],
    },
    "Bilawal": {
        "rasa": "Utsaha / Hasya (Radiant Morning, Joy, Celebration)",
        "mood": "happy",
        "notes": [".Dha", ".Ni", "Sa", "Re", "Ga", "Ma", "Pa", "Dha", "Ni", "Sa'", "Re'"],
        "aaroha": ["Sa", "Re", "Ga", "Ma", "Pa", "Dha", "Ni", "Sa'"],
        "avaroha": ["Sa'", "Ni", "Dha", "Pa", "Ma", "Ga", "Re", "Sa"],
        "vadi": "Dha",
        "samvadi": "Ga",
        "andolan": ["Dha", "Ga"],
        "drone": "Pa",
        "tempo": 1.00,
        "default_tala": "Teental",
        "pakad": [
            ["Ga", "Re", "Ga", "Ma", "Pa", "Dha", "Ni", "Sa'"],
            ["Dha", "Pa", "Ma", "Ga", "Ma", "Re", "Sa"],
        ],
    },
    "Hamsadhwani": {
        "rasa": "Mangala / Utsaha (Triumph, Sparkling Celebration, Flight)",
        "mood": "triumphant",
        "notes": [".Ni", "Sa", "Re", "Ga", "Pa", "Ni", "Sa'", "Re'", "Ga'"],
        "aaroha": ["Sa", "Re", "Ga", "Pa", "Ni", "Sa'"],
        "avaroha": ["Sa'", "Ni", "Pa", "Ga", "Re", "Sa"],
        "vadi": "Sa",
        "samvadi": "Pa",
        "andolan": ["Ga", "Ni"],
        "drone": "Pa",
        "tempo": 1.05,
        "default_tala": "Teental",
        "pakad": [
            ["Sa", "Re", "Ga", "Pa", "Ni", "Sa'"],
            ["Ni", "Pa", "Ga", "Re", ".Ni", "Sa"],
        ],
    },
    "Charukeshi": {
        "rasa": "Viraha / Shringara (Bittersweet Catharsis, Cinematic Yearning)",
        "mood": "bittersweet",
        "notes": [".dha", ".ni", "Sa", "Re", "Ga", "Ma", "Pa", "dha", "ni", "Sa'", "Re'"],
        "aaroha": ["Sa", "Re", "Ga", "Ma", "Pa", "dha", "ni", "Sa'"],
        "avaroha": ["Sa'", "ni", "dha", "Pa", "Ma", "Ga", "Re", "Sa"],
        "vadi": "Pa",
        "samvadi": "Sa",
        "andolan": ["dha", "Ga"],
        "drone": "Pa",
        "tempo": 0.90,
        "default_tala": "Keherwa",
        "pakad": [
            ["Sa", "Re", "Ga", "Ma", "Pa", "dha", "Pa"],
            ["dha", "ni", "Pa", "Ma", "Ga", "Re", "Sa"],
        ],
    },
    "Bhairav": {
        "rasa": "Bhakti / Adbhuta (Sacred Dawn, Reverence, Timeless Wonder)",
        "mood": "sacred",
        "notes": [".dha", ".Ni", "Sa", "re", "Ga", "Ma", "Pa", "dha", "Ni", "Sa'", "re'"],
        "aaroha": ["Sa", "re", "Ga", "Ma", "Pa", "dha", "Ni", "Sa'"],
        "avaroha": ["Sa'", "Ni", "dha", "Pa", "Ma", "Ga", "re", "Sa"],
        "vadi": "dha",
        "samvadi": "re",
        "andolan": ["re", "dha"],
        "drone": "Pa",
        "tempo": 0.84,
        "default_tala": "Keherwa",
        "pakad": [
            ["Ga", "Ma", "dha", "dha", "Pa"],
            ["Ga", "Ma", "re", "re", "Sa"],
        ],
    },
    "Shivaranjani": {
        "rasa": "Karuna / Viraha (Poignant Melancholy, Solitude, Longing)",
        "mood": "sad",
        "notes": [".Dha", "Sa", "Re", "ga", "Pa", "Dha", "Sa'", "Re'", "ga'"],
        "aaroha": ["Sa", "Re", "ga", "Pa", "Dha", "Sa'"],
        "avaroha": ["Sa'", "Dha", "Pa", "ga", "Re", "Sa"],
        "vadi": "Pa",
        "samvadi": "Sa",
        "andolan": ["ga", "Dha"],
        "drone": "Pa",
        "tempo": 0.86,
        "default_tala": "Dadra",
        "pakad": [
            ["Sa", "Re", "ga", "Pa", "Dha", "Sa'"],
            ["Dha", "Pa", "ga", "Re", ".Dha", "Sa"],
        ],
    },
    "Bhairavi": {
        "rasa": "Karuna / Bhakti (Deep Soulful Pathos, Transcendence, Finale)",
        "mood": "soulful_sad",
        "notes": [".dha", ".ni", "Sa", "re", "ga", "Ma", "Pa", "dha", "ni", "Sa'", "re'", "ga'"],
        "aaroha": ["Sa", "re", "ga", "Ma", "Pa", "dha", "ni", "Sa'"],
        "avaroha": ["Sa'", "ni", "dha", "Pa", "Ma", "ga", "re", "Sa"],
        "vadi": "Ma",
        "samvadi": "Sa",
        "andolan": ["re", "ga", "dha"],
        "drone": "Pa",
        "tempo": 0.85,
        "default_tala": "Dadra",
        "pakad": [
            [".ni", "Sa", "ga", "Ma", "Pa", "dha", "Pa"],
            ["Ma", "ga", "re", "Sa", ".ni", "Sa"],
        ],
    },
    "Darbari": {
        "rasa": "Gambhira / Karuna (Midnight Majesty, Profound Grief, Gravity)",
        "mood": "tragic_majestic",
        "notes": [".dha", ".ni", "Sa", "Re", "ga", "Ma", "Pa", "dha", "ni", "Sa'", "Re'"],
        "aaroha": [".ni", "Sa", "Re", "ga", "Ma", "Pa", "dha", "ni", "Sa'"],
        "avaroha": ["Sa'", "dha", "ni", "Pa", "Ma", "Pa", "ga", "Ma", "Re", "Sa"],
        "vadi": "Re",
        "samvadi": "Pa",
        "andolan": ["ga", "dha"],
        "drone": "Pa",
        "tempo": 0.80,
        "default_tala": "Keherwa",
        "pakad": [
            [".dha", ".ni", "Sa", "Re", "ga", "Re", "Sa"],
            ["Ma", "Pa", "dha", "ni", "Pa", "ga", "Ma", "Re", "Sa"],
        ],
    },
    "Malkauns": {
        "rasa": "Veera / Adbhuta (Cosmic Night, Meditative Power, Mystery)",
        "mood": "mystic_heroic",
        "notes": [".dha", ".ni", "Sa", "ga", "Ma", "dha", "ni", "Sa'", "ga'"],
        "aaroha": [".ni", "Sa", "ga", "Ma", "dha", "ni", "Sa'"],
        "avaroha": ["Sa'", "ni", "dha", "Ma", "ga", "Sa"],
        "vadi": "Ma",
        "samvadi": "Sa",
        "andolan": ["ga", "dha", "ni"],
        "drone": "Ma",
        "tempo": 0.88,
        "default_tala": "Keherwa",
        "pakad": [
            [".ni", "Sa", "ga", "Ma", "ga", "Sa"],
            ["Ma", "dha", "ni", "Sa'", "ni", "dha", "Ma"],
        ],
    },
}


# ==============================================================================
# 3. SONG STRUCTURE PARSER (PRESERVING POETIC LINES & METER)
# ==============================================================================

SECTION_RE = re.compile(
    r"^\[?\s*(verse|chorus|bridge|pre-chorus|outro|intro|hook|refrain|interlude|alap|finale)"
    r"(?:\s*\d+)?\s*\]?\s*:?\s*$",
    re.IGNORECASE,
)


def parse_song(raw: str) -> List[Dict]:
    """
    Parse raw lyrics into structured sections while preserving individual
    poetic lines (`lines` list) as well as combined `text`.
    """
    sections: List[Dict] = []
    cur_label: Optional[str] = None
    cur_lines: List[str] = []
    auto_idx = 0
    auto_labels = ["Verse 1", "Chorus", "Verse 2", "Chorus", "Bridge", "Chorus", "Outro"]

    for raw_line in raw.strip().splitlines():
        line = raw_line.strip()
        if SECTION_RE.match(line) or (line.endswith(":") and len(line) < 22 and " " not in line[:-1]):
            if cur_lines:
                label = cur_label or auto_labels[auto_idx % len(auto_labels)]
                sections.append({
                    "label": label,
                    "lines": list(cur_lines),
                    "text": " ".join(cur_lines),
                })
                if cur_label is None:
                    auto_idx += 1
            cur_label = line.strip("[]:\t ")
            cur_lines = []
        elif line == "":
            if cur_lines:
                label = cur_label or auto_labels[auto_idx % len(auto_labels)]
                sections.append({
                    "label": label,
                    "lines": list(cur_lines),
                    "text": " ".join(cur_lines),
                })
                cur_label = None
                cur_lines = []
                auto_idx += 1
        else:
            cur_lines.append(line)

    if cur_lines:
        label = cur_label or auto_labels[auto_idx % len(auto_labels)]
        sections.append({
            "label": label,
            "lines": list(cur_lines),
            "text": " ".join(cur_lines),
        })

    if not sections:
        clean_raw = raw.strip() or "Om Shanti"
        sections = [{"label": "Song", "lines": [clean_raw], "text": clean_raw}]

    return sections


# ==============================================================================
# 4. NAVARASA POETIC SENTIMENT & RAGA SELECTION ENGINE
# ==============================================================================

LEXICON = {
    "sorrow": {
        "sorrow", "sadness", "sad", "parting", "tears", "tear", "cry", "crying", "weep",
        "alone", "lonely", "lost", "broken", "pain", "grief", "ache", "aching", "hurt",
        "shadow", "shadows", "dark", "darkness", "fade", "fading", "goodbye", "farewell",
        "empty", "cold", "grave", "wound", "bleed", "mourning", "sigh", "regret", "ash",
        "ashes", "dust", "shattered", "fall", "falling", "drown", "ghost", "gone",
    },
    "peace_nature": {
        "stillness", "still", "morning", "dawn", "river", "banyan", "ancient", "peace",
        "peaceful", "calm", "quiet", "silence", "silent", "breeze", "wind", "mountain",
        "mountains", "sea", "ocean", "sky", "clouds", "tree", "trees", "forest", "lotus",
        "temple", "prayer", "sacred", "holy", "grace", "light", "moon", "moonlight",
        "breath", "breathe", "flow", "flowing", "earth", "rain", "monsoon", "garden",
    },
    "yearning_love": {
        "home", "belong", "heart", "love", "lover", "beloved", "calling", "call", "need",
        "needs", "carry", "bring", "back", "wait", "waiting", "dream", "dreams", "hold",
        "touch", "kiss", "embrace", "memory", "memories", "remember", "wish", "hope",
        "soul", "desire", "burn", "burning", "forever", "always", "together", "distance",
        "somewhere", "find", "finds", "meet", "return", "arms",
    },
    "joy_triumph": {
        "joy", "happy", "smile", "laugh", "laughter", "dance", "dancing", "sing",
        "singing", "celebrate", "shine", "shining", "bright", "sun", "sunshine", "gold",
        "golden", "rise", "rising", "fly", "flying", "wings", "free", "freedom", "victory",
        "win", "glory", "bloom", "blossom", "alive", "awakening", "rejoice", "fireworks",
    },
    "mystic_power": {
        "night", "midnight", "stars", "star", "cosmos", "universe", "infinite", "eternal",
        "eternity", "storm", "thunder", "lightning", "fire", "flame", "power", "destiny",
        "fate", "mystery", "secret", "deep", "abyss", "king", "crown", "warrior", "brave",
        "fearless", "immortal", "awaken",
    },
}


def analyze_rasa(text: str, label: str = "") -> Dict[str, float]:
    """Compute multidimensional Navarasa emotional scores for lyrics text."""
    words = [re.sub(r"[^a-z']", "", w.lower()) for w in text.split()]
    words = [w for w in words if w]
    n_words = max(1, len(words))

    counts = {k: 0.0 for k in LEXICON}
    for w in words:
        for cat, vocab in LEXICON.items():
            if w in vocab:
                counts[cat] += 1.0

    blob = TextBlob(text)
    polarity = float(blob.sentiment.polarity)
    subjectivity = float(blob.sentiment.subjectivity)

    # Normalize lexical densities
    scale = 10.0 / math.sqrt(n_words)
    sorrow = counts["sorrow"] * scale + max(0.0, -polarity) * 1.8
    joy = counts["joy_triumph"] * scale + max(0.0, polarity) * 1.6
    peace = counts["peace_nature"] * scale + (1.0 - abs(polarity)) * 0.6
    yearning = counts["yearning_love"] * scale + subjectivity * 0.9
    mystic = counts["mystic_power"] * scale

    # Detect bittersweet contrast (requires clear sorrow/loss paired with light/hope/yearning)
    bittersweet = 0.0
    if counts["sorrow"] >= 1.5 and (counts["peace_nature"] > 0 or counts["yearning_love"] > 0 or counts["joy_triumph"] > 0):
        bittersweet = (counts["sorrow"] + counts["yearning_love"] + 0.5 * counts["peace_nature"]) * scale * 0.95

    return {
        "polarity": polarity,
        "subjectivity": subjectivity,
        "sorrow": sorrow,
        "joy": joy,
        "peace": peace,
        "yearning": yearning,
        "mystic": mystic,
        "bittersweet": bittersweet,
    }


def pick_raga(text: str, label: str = "", forced_raga: Optional[str] = None) -> Tuple[str, Dict]:
    """
    Select the ideal Raga for a section using Navarasa emotional analysis
    and structural role (Verse / Chorus / Bridge / Outro).
    """
    if forced_raga and forced_raga in RAGAS:
        return forced_raga, RAGAS[forced_raga]

    scores = analyze_rasa(text, label)
    lbl = label.lower()

    # Check bittersweet contrast first (e.g., "no darkness without light / Every parting every sadness / somewhere I belong"
    # or "Let the wind carry my sorrow / And bring me back to me")
    if scores["bittersweet"] >= 1.6:
        if "bridge" in lbl:
            raga = "Charukeshi"
        elif "chorus" in lbl:
            raga = "Desh"
        elif "outro" in lbl:
            raga = "Bhairavi"
        else:
            raga = "Charukeshi"
    elif scores["sorrow"] > max(scores["joy"], scores["peace"]) + 0.4:
        if "outro" in lbl or "finale" in lbl:
            raga = "Bhairavi"
        elif "bridge" in lbl or scores["mystic"] > 0.8:
            raga = "Darbari"
        else:
            raga = "Shivaranjani"
    elif scores["joy"] > max(scores["sorrow"], scores["peace"]) + 0.35:
        if "chorus" in lbl or "hook" in lbl:
            raga = "Hamsadhwani" if scores["joy"] > 2.2 else "Desh"
        else:
            raga = "Bilawal"
    elif scores["mystic"] > max(scores["peace"], scores["yearning"]) + 0.3:
        raga = "Malkauns" if "bridge" in lbl or "verse" in lbl else "Bhairav"
    elif scores["yearning"] > scores["peace"] + 0.25:
        raga = "Desh" if "chorus" in lbl else "Yaman"
    else:
        # Serene / Nature / Spiritual
        if "morning" in text.lower() or "dawn" in text.lower() or "ancient" in text.lower():
            raga = "Yaman" if "chorus" in lbl else ("Bhairav" if scores["mystic"] > 0.5 else "Yaman")
        elif "chorus" in lbl:
            raga = "Desh"
        elif "outro" in lbl:
            raga = "Bhairavi"
        else:
            raga = "Yaman"

    return raga, RAGAS[raga]


# ==============================================================================
# 5. PROSODY, SYLLABLES & BEAT-LOCKED MELODIC SEQUENCE BUILDER
# ==============================================================================

FUNCTION_WORDS = {
    "a", "an", "the", "in", "of", "to", "and", "or", "but", "for", "with", "on",
    "at", "by", "from", "as", "into", "is", "are", "was", "were", "be", "been",
    "it", "its", "my", "your", "our", "their", "his", "her", "me", "you", "we",
    "they", "i", "that", "this", "what", "where", "when", "who",
}


def syllables(word: str) -> int:
    """Accurate English poetic syllable counter."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    if len(w) <= 3:
        return 1

    # Handle common compound silent-e patterns ('somewhere', 'someone', 'something', 'sometimes', 'lonely', 'lately')
    for prefix in ("some", "where", "there", "here", "home", "lone", "late", "safe", "time", "life", "love"):
        if w.startswith(prefix) and len(w) > len(prefix) + 1:
            w = prefix[:-1] + w[len(prefix):]
            break

    # Remove silent trailing 'e', 'es', 'ed' (except after t/d for ed, or s/z/x/ch/sh for es)
    if w.endswith("e") and not w.endswith("le") and not w.endswith("ee"):
        w = w[:-1]
    elif w.endswith("ed") and len(w) > 4 and w[-3] not in "td":
        w = w[:-2]
    elif w.endswith("es") and len(w) > 4 and w[-3] not in "szx":
        w = w[:-2]

    vowel_runs = re.findall(r"[aeiouy]+", w)
    count = len(vowel_runs)

    # Handle syllabic 'le' at end of word (e.g., 'gentle', 'little')
    if word.lower().endswith("le") and len(word) > 2 and word.lower()[-3] not in "aeiouy":
        count += 1

    return max(1, count)


def word_beats(word: str, is_line_end: bool, is_section_end: bool) -> float:
    """
    Compute the musical duration of a word in *beats* (matras) so that
    every word locks tightly to the Tala rhythmic grid.
    """
    clean = re.sub(r"[^a-z']", "", word.lower())
    s = syllables(clean)
    is_func = clean in FUNCTION_WORDS

    if is_section_end:
        return 2.0
    if is_line_end:
        return 1.5 if s >= 2 else 1.0

    if s == 1:
        return 0.5 if is_func else 0.5
    elif s == 2:
        return 1.0
    elif s == 3:
        return 1.5
    else:
        return 2.0


def note_duration(word: str, tempo: float, bpm: float = 84.0) -> float:
    """Convert word syllable count into beat-synchronized duration in seconds."""
    beat_sec = 60.0 / max(40.0, bpm)
    s = syllables(word)
    clean = re.sub(r"[^a-z']", "", word.lower())
    if s <= 1:
        beats = 0.5 if clean in FUNCTION_WORDS else 0.5
    elif s == 2:
        beats = 1.0
    else:
        beats = 1.5
    return round(beats * beat_sec, 4)


@dataclass
class NoteEvent:
    """Represents a single musical event (word or sub-syllable melisma/rest)."""
    word: str
    note: str
    dur: float
    beats: float
    is_rest: bool = False
    is_glide: bool = False
    has_kan: bool = False
    has_andolan: bool = False
    accent: float = 0.85
    line_idx: int = 0
    sub_notes: List[Tuple[str, float]] = field(default_factory=list)


def build_sequence(
    section: Dict,
    bpm: float = 84.0,
    forced_raga: Optional[str] = None,
    motif_cache: Optional[Dict[str, List[NoteEvent]]] = None,
) -> Tuple[List[Tuple[str, str, float]], List[NoteEvent], str, Dict]:
    """
    Build both the classic `(word, note, dur)` sequence and rich `NoteEvent`
    phrasing sequence for a song section, locked to the Tala beat grid.
    """
    raga_name, raga = pick_raga(section["text"], section["label"], forced_raga=forced_raga)
    notes: List[str] = raga["notes"]
    vadi: str = raga["vadi"]
    samvadi: str = raga["samvadi"]
    andolan_notes = set(raga.get("andolan", []))
    pakads: List[List[str]] = raga.get("pakad", [])

    beat_sec = 60.0 / max(40.0, bpm)
    lbl_lower = section["label"].lower()
    is_chorus = "chorus" in lbl_lower or "hook" in lbl_lower or "refrain" in lbl_lower
    is_bridge = "bridge" in lbl_lower
    is_outro = "outro" in lbl_lower or "finale" in lbl_lower

    # Check if we already composed a melodic motif for identical chorus text
    cache_key = f"{raga_name}::{section['text'].strip().lower()}"
    if is_chorus and motif_cache is not None and cache_key in motif_cache:
        cached_events = []
        for ev in motif_cache[cache_key]:
            cached_events.append(NoteEvent(
                word=ev.word,
                note=ev.note,
                dur=ev.dur,
                beats=ev.beats,
                is_rest=ev.is_rest,
                is_glide=ev.is_glide,
                has_kan=ev.has_kan,
                has_andolan=ev.has_andolan,
                accent=min(1.0, ev.accent * 1.06),  # Final chorus sings with heightened intensity
                line_idx=ev.line_idx,
                sub_notes=list(ev.sub_notes),
            ))
        legacy_seq = [(e.word, e.note, round(e.dur, 3)) for e in cached_events if not e.is_rest]
        return legacy_seq, cached_events, raga_name, raga

    sa_idx = notes.index("Sa") if "Sa" in notes else 1
    vadi_idx = notes.index(vadi) if vadi in notes else len(notes) // 2
    samvadi_idx = notes.index(samvadi) if samvadi in notes else max(0, len(notes) - 3)
    pa_idx = notes.index("Pa") if "Pa" in notes else vadi_idx
    sa_upper_idx = notes.index("Sa'") if "Sa'" in notes else len(notes) - 1

    lines: List[str] = section.get("lines") or [section["text"]]
    events: List[NoteEvent] = []
    legacy_seq: List[Tuple[str, str, float]] = []

    # Starting note depends on section role (Asthayi starts near Sa/Vadi; Antara/Chorus climbs higher)
    idx = vadi_idx if is_chorus else (pa_idx if is_bridge else sa_idx)
    maxi = len(notes) - 1

    for line_i, line in enumerate(lines):
        raw_words = [w for w in line.split() if re.sub(r"[^a-zA-Z0-9']", "", w)]
        if not raw_words:
            continue

        line_beats_accum = 0.0
        n_w = len(raw_words)

        # Choose a characteristic Pakad motif to inspire the start of lines 0 and 2
        active_pakad = pakads[line_i % len(pakads)] if pakads else []

        for w_i, word in enumerate(raw_words):
            clean = re.sub(r"[^a-z']", "", word.lower())
            if not clean:
                continue

            is_line_end = (w_i == n_w - 1)
            is_sec_end = is_line_end and (line_i == len(lines) - 1)
            s = syllables(clean)
            is_func = clean in FUNCTION_WORDS

            beats = word_beats(clean, is_line_end, is_sec_end)
            line_beats_accum += beats
            dur = beats * beat_sec

            # Melodic contour with phrasing arc (Arch contour per line + Pakad attraction)
            line_progress = w_i / max(1, n_w - 1)
            if w_i < len(active_pakad) and (line_i % 2 == 0) and w_i <= 2 and active_pakad[w_i] in notes:
                idx = notes.index(active_pakad[w_i])
            elif is_sec_end:
                # Section resolution lands on Sa (or Vadi in Bridge)
                idx = vadi_idx if is_bridge else sa_idx
            elif is_line_end:
                # Line cadence resolves to Vadi (open phrase on odd lines) or Sa/Pa (closed phrase on even lines)
                if line_i % 2 == 0:
                    idx = vadi_idx if abs(idx - vadi_idx) <= 4 else pa_idx
                else:
                    idx = sa_idx if idx < pa_idx else (sa_upper_idx if is_chorus and line_i == 1 else pa_idx)
            else:
                # Melodic arch within the line: ascend in first half, descend toward cadence in second half
                word_hash = int(hashlib.md5(clean.encode("utf-8")).hexdigest()[:4], 16)
                step = 1 if (s == 1 or is_func) else (2 if word_hash % 3 == 0 else 1)

                if line_progress < 0.55:
                    # Ascending arch toward Vadi / Samvadi / Sa' (higher peak in Chorus & Bridge)
                    target = sa_upper_idx if (is_chorus or is_bridge) else max(vadi_idx, pa_idx)
                    direction = 1 if idx < target else (-1 if word_hash % 2 == 0 else 1)
                else:
                    # Descending arch back toward Vadi / Sa
                    target = vadi_idx if line_i % 2 == 0 else sa_idx
                    direction = -1 if idx > target else (1 if idx < target else 0)

                idx = max(0, min(maxi, idx + direction * step))

            primary_note = notes[idx]

            # Build melismatic sub-notes (Swara Vistara) for multi-syllable content words
            sub_notes: List[Tuple[str, float]] = []
            if s >= 2 and not is_func and beats >= 1.0:
                neighbor_dir = -1 if (is_line_end or line_progress > 0.6) else 1
                neighbor_idx = max(0, min(maxi, idx + neighbor_dir))
                if neighbor_idx == idx:
                    neighbor_idx = max(0, idx - 1)
                neighbor_note = notes[neighbor_idx]

                if s == 2 or beats == 1.0:
                    sub_notes = [(primary_note, dur * 0.62), (neighbor_note, dur * 0.38)]
                    idx = neighbor_idx
                else:
                    # 3+ syllables: graceful 3-note ornament (e.g. Ga -> ma -> Ga or Sa -> Re -> Ga)
                    third_idx = idx if is_line_end else max(0, min(maxi, neighbor_idx + neighbor_dir))
                    if third_idx == neighbor_idx:
                        third_idx = idx
                    sub_notes = [
                        (primary_note, dur * 0.45),
                        (neighbor_note, dur * 0.30),
                        (notes[third_idx], dur * 0.25),
                    ]
                    idx = third_idx
            else:
                sub_notes = [(primary_note, dur)]

            # Expressive articulations
            is_glide = (clean[0] in "aeiouywhmlrn") or (s >= 2) or is_line_end
            has_kan = (not is_func) and (w_i % 2 == 0)
            has_andolan = (primary_note in andolan_notes) or (dur >= beat_sec * 1.0)
            accent = 0.72 if is_func else (0.98 if is_chorus else 0.88)

            ev = NoteEvent(
                word=word,
                note=primary_note,
                dur=dur,
                beats=beats,
                is_rest=False,
                is_glide=is_glide,
                has_kan=has_kan,
                has_andolan=has_andolan,
                accent=accent,
                line_idx=line_i,
                sub_notes=sub_notes,
            )
            events.append(ev)
            legacy_seq.append((word, primary_note, round(dur, 3)))

        # Pad the end of each poetic line to the next 4-beat (or 2-beat) Tala bar boundary!
        # This guarantees that the next poetic line enters squarely on the Tabla beat!
        bar_quantum = 4.0
        remainder = line_beats_accum % bar_quantum
        if remainder > 1e-4:
            pad_beats = bar_quantum - remainder
        else:
            pad_beats = 1.0  # Give a 1-beat breath if line already filled the bar

        # Split pad into extra sustain on the line-ending word + a natural breath rest
        if events and not events[-1].is_rest:
            sustain_add_beats = min(pad_beats * 0.5, 1.0)
            rest_beats = pad_beats - sustain_add_beats
            if sustain_add_beats > 0:
                add_sec = sustain_add_beats * beat_sec
                events[-1].dur += add_sec
                events[-1].beats += sustain_add_beats
                if events[-1].sub_notes:
                    last_sw, last_d = events[-1].sub_notes[-1]
                    events[-1].sub_notes[-1] = (last_sw, last_d + add_sec)
                legacy_seq[-1] = (legacy_seq[-1][0], legacy_seq[-1][1], round(events[-1].dur, 3))
        else:
            rest_beats = pad_beats

        if rest_beats > 0.05:
            events.append(NoteEvent(
                word="[breath]",
                note="Sa",
                dur=rest_beats * beat_sec,
                beats=rest_beats,
                is_rest=True,
                line_idx=line_i,
            ))

    if is_chorus and motif_cache is not None:
        motif_cache[cache_key] = list(events)

    return legacy_seq, events, raga_name, raga


# ==============================================================================
# 6. EXPRESSIVE CONTINUOUS-PHASE LEAD & INSTRUMENT SYNTHESIS ENGINE
# ==============================================================================

def adsr(n: int, sr: int = SAMPLE_RATE, a: float = 0.04, d: float = 0.08, sus: float = 0.80, r: float = 0.10) -> np.ndarray:
    """Smooth raised-cosine ADSR envelope."""
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    a_s = min(int(a * sr), n // 3)
    d_s = min(int(d * sr), n // 4)
    r_s = min(int(r * sr), n // 3)
    s_s = max(0, n - a_s - d_s - r_s)

    attack = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, a_s))) if a_s > 0 else np.zeros(0)
    decay = sus + (1.0 - sus) * 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, d_s))) if d_s > 0 else np.zeros(0)
    sustain = np.full(s_s, sus, dtype=np.float64)
    release = sus * 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, r_s))) if r_s > 0 else np.zeros(0)

    env = np.concatenate([attack, decay, sustain, release])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)), mode="edge")
    return env[:n]


def synth_note(freq: float, dur: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Backwards-compatible single-note synthesizer with warm Bansuri harmonics & vibrato."""
    n = max(1, int(dur * sr))
    t = np.arange(n, dtype=np.float64) / sr
    env = adsr(n, sr, a=0.045, d=0.09, sus=0.78, r=0.11)

    # Delayed microtonal vibrato (Andolan)
    vib_onset = np.clip((t - 0.10) / 0.15, 0.0, 1.0)
    inst_freq = freq * (1.0 + 0.008 * vib_onset * np.sin(2.0 * np.pi * 5.2 * t))
    phase = 2.0 * np.pi * np.cumsum(inst_freq) / sr

    harmonics = [(1, 1.00), (2, 0.40), (3, 0.18), (4, 0.07), (5, 0.03)]
    wave_out = sum(amp * np.sin(h * phase) for h, amp in harmonics)
    wave_out /= sum(amp for _, amp in harmonics)
    return wave_out * env


def render_expressive_phrase(
    events: List[NoteEvent],
    raga: Dict,
    freqs: Dict[str, float],
    sr: int = SAMPLE_RATE,
    lead_style: str = "bansuri_sarangi",
    rng: Optional[np.random.Generator] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Render a section's NoteEvents as a continuous-phase expressive performance
    with true Meend (pitch glides), Kan Swara (grace notes), Andolan (microtonal
    oscillation), Bansuri breath turbulence, Bowed Sarangi formant warmth, and
    Sitar Jawari pluck accents.
    Returns (stereo_left, stereo_right).
    """
    if rng is None:
        rng = np.random.default_rng(42)

    notes_list = raga["notes"]
    andolan_set = set(raga.get("andolan", []))

    # Expand NoteEvents into sub-note segments
    segments: List[Dict] = []
    for ev in events:
        if ev.is_rest:
            segments.append({
                "freq": freqs.get(ev.note, freqs["Sa"]),
                "swara": ev.note,
                "dur": ev.dur,
                "is_rest": True,
                "is_glide": False,
                "has_kan": False,
                "has_andolan": False,
                "accent": 0.0,
                "is_sub": False,
            })
        else:
            subs = ev.sub_notes if ev.sub_notes else [(ev.note, ev.dur)]
            for s_i, (sw, s_dur) in enumerate(subs):
                f_hz = freqs.get(sw, freqs["Sa"])
                segments.append({
                    "freq": f_hz,
                    "swara": sw,
                    "dur": s_dur,
                    "is_rest": False,
                    "is_glide": True if s_i > 0 else ev.is_glide,
                    "has_kan": ev.has_kan and (s_i == 0),
                    "has_andolan": (sw in andolan_set) or (s_dur >= 0.32),
                    "accent": ev.accent * (0.94 if s_i > 0 else 1.0),
                    "is_sub": (s_i > 0),
                })

    total_samples = sum(max(1, int(round(seg["dur"] * sr))) for seg in segments)
    if total_samples <= 0:
        return np.zeros(1), np.zeros(1)

    freq_curve = np.zeros(total_samples, dtype=np.float64)
    amp_curve = np.zeros(total_samples, dtype=np.float64)
    chiff_curve = np.zeros(total_samples, dtype=np.float64)
    sitar_track = np.zeros(total_samples, dtype=np.float64)

    pos = 0
    prev_freq = freqs.get("Sa", 261.63)
    prev_was_rest = True

    for i, seg in enumerate(segments):
        n = max(1, int(round(seg["dur"] * sr)))
        if pos + n > total_samples:
            n = total_samples - pos
        if n <= 0:
            break

        f_target = seg["freq"]
        next_is_rest = (i == len(segments) - 1) or segments[i + 1]["is_rest"]
        next_is_glide = (not next_is_rest) and segments[i + 1]["is_glide"]

        if seg["is_rest"]:
            freq_curve[pos:pos + n] = prev_freq
            amp_curve[pos:pos + n] = 0.0
            prev_was_rest = True
            pos += n
            continue

        t_local = np.arange(n, dtype=np.float64) / sr
        f_seg = np.full(n, f_target, dtype=np.float64)

        # 1. Meend (Glissando) from previous note or Kan Swara grace inflection
        if not prev_was_rest and seg["is_glide"] and abs(f_target - prev_freq) > 1.0:
            # True S-curve Meend over 70-130ms
            glide_dur = min(0.12 if seg["is_sub"] else 0.085, seg["dur"] * 0.45)
            g_n = max(1, int(glide_dur * sr))
            s_curve = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, g_n)))
            f_seg[:g_n] = prev_freq + (f_target - prev_freq) * s_curve
        elif seg["has_kan"]:
            # Kan Swara: rapid 40ms grace note from upper scale neighbor
            sw = seg["swara"]
            sw_idx = notes_list.index(sw) if sw in notes_list else 0
            kan_sw = notes_list[min(len(notes_list) - 1, sw_idx + 1)]
            f_kan = freqs.get(kan_sw, f_target * 1.125)
            k_n = min(int(0.042 * sr), n // 3)
            if k_n > 1:
                s_curve = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, k_n)))
                f_seg[:k_n] = f_kan + (f_target - f_kan) * s_curve

        # 2. Andolan & Expressive Vibrato on sustained notes
        if seg["has_andolan"]:
            is_komal_andolan = seg["swara"] in ("re", "ga", "dha", "ni")
            vib_rate = 4.3 if is_komal_andolan else 5.4
            vib_depth = 0.013 if is_komal_andolan else 0.0075
            vib_env = np.clip((t_local - 0.08) / 0.14, 0.0, 1.0)
            # Fade out vibrato slightly at very end of note
            f_seg *= 1.0 + vib_depth * vib_env * np.sin(2.0 * np.pi * vib_rate * t_local)

        freq_curve[pos:pos + n] = f_seg

        # 3. Legato-aware Amplitude Envelope + Breath Chiff
        env_seg = np.ones(n, dtype=np.float64) * seg["accent"]
        if prev_was_rest:
            a_n = min(int(0.055 * sr), n // 3)
            if a_n > 1:
                env_seg[:a_n] *= 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, a_n)))
                chiff_curve[pos:pos + a_n] = np.sin(np.linspace(0.0, np.pi, a_n)) * seg["accent"]
        elif seg["is_sub"]:
            # Melisma within a word: seamless legato with subtle 12% breath dip
            a_n = min(int(0.025 * sr), n // 4)
            if a_n > 1:
                env_seg[:a_n] *= 0.88 + 0.12 * 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, a_n)))
        else:
            # Articulated syllable transition: 35% tongue/bow dip
            a_n = min(int(0.032 * sr), n // 4)
            if a_n > 1:
                env_seg[:a_n] *= 0.65 + 0.35 * 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, a_n)))
                chiff_curve[pos:pos + a_n] = 0.55 * np.sin(np.linspace(0.0, np.pi, a_n)) * seg["accent"]

        if next_is_rest:
            r_n = min(int(0.11 * sr), n // 2)
            if r_n > 1:
                env_seg[-r_n:] *= 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, r_n)))
        elif not next_is_glide:
            r_n = min(int(0.025 * sr), n // 4)
            if r_n > 1:
                env_seg[-r_n:] *= 0.68 + 0.32 * 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, r_n)))

        amp_curve[pos:pos + n] = env_seg

        # 4. Trigger Sitar Jawari pluck on phrase starts and accented non-sub notes
        if not seg["is_sub"] and (prev_was_rest or seg["accent"] >= 0.85):
            pluck_len = min(int(1.1 * sr), total_samples - pos)
            if pluck_len > int(0.05 * sr):
                sitar_pluck = synth_sitar_pluck(f_target, pluck_len / sr, sr=sr) * (0.45 * seg["accent"])
                sitar_track[pos:pos + pluck_len] += sitar_pluck[:pluck_len]

        prev_freq = f_target
        prev_was_rest = False
        pos += n

    # Smooth amp_curve slightly to prevent any micro-zipper artifacts
    smooth_win = max(3, int(0.004 * sr))
    kernel = np.ones(smooth_win) / smooth_win
    amp_curve = np.convolve(amp_curve, kernel, mode="same")

    # Continuous Phase Integration across the entire section
    phase = 2.0 * np.pi * np.cumsum(freq_curve) / sr

    # --- Instrument A: Concert Bansuri (Warm Bamboo Flute + Breath Turbulence) ---
    h1 = np.sin(phase)
    h2 = 0.44 * amp_curve * np.sin(2.0 * phase + 0.25)
    h3 = 0.20 * (amp_curve ** 1.4) * np.sin(3.0 * phase + 0.60)
    h4 = 0.07 * (amp_curve ** 1.8) * np.sin(4.0 * phase + 1.10)
    bansuri_core = (h1 + h2 + h3 + h4) / 1.55

    # Breath turbulence & embouchure chiff (bandpass filtered noise)
    raw_noise = rng.standard_normal(total_samples)
    sos_breath = signal.butter(2, [1400.0 / (sr / 2), 3800.0 / (sr / 2)], btype="bandpass", output="sos")
    breath_noise = signal.sosfilt(sos_breath, raw_noise)
    breath_layer = breath_noise * (0.028 * amp_curve + 0.065 * chiff_curve) * (1.0 + 0.45 * h1)
    bansuri = (bansuri_core + breath_layer) * amp_curve

    # --- Instrument B: Soulful Bowed Sarangi / Solo Cello (Vocal Formant Filtered) ---
    bow_raw = np.zeros(total_samples, dtype=np.float64)
    for h in range(1, 9):
        sign = 1.0 if h % 2 == 1 else -0.85
        bow_raw += (sign / (h ** 1.05)) * np.sin(h * phase + 0.17 * h)
    # Apply vocal formant resonances (F1 ~ 520 Hz, F2 ~ 1420 Hz, F3 ~ 2650 Hz)
    sos_f1 = signal.butter(2, [380.0 / (sr / 2), 700.0 / (sr / 2)], btype="bandpass", output="sos")
    sos_f2 = signal.butter(2, [1150.0 / (sr / 2), 1750.0 / (sr / 2)], btype="bandpass", output="sos")
    sos_f3 = signal.butter(2, [2200.0 / (sr / 2), 3100.0 / (sr / 2)], btype="bandpass", output="sos")
    sarangi = (
        0.55 * signal.sosfilt(sos_f1, bow_raw)
        + 0.32 * signal.sosfilt(sos_f2, bow_raw)
        + 0.15 * signal.sosfilt(sos_f3, bow_raw)
        + 0.30 * h1
    ) * amp_curve

    # Blend Bansuri, Sarangi, and Sitar based on section mood/style
    mood = raga.get("mood", "peaceful")
    if mood in ("sad", "soulful_sad", "tragic_majestic", "bittersweet"):
        w_bansuri, w_sarangi, w_sitar = 0.56, 0.44, 0.32
    elif mood in ("happy", "triumphant", "warm_joy"):
        w_bansuri, w_sarangi, w_sitar = 0.65, 0.25, 0.45
    else:
        w_bansuri, w_sarangi, w_sitar = 0.64, 0.30, 0.36

    left = w_bansuri * bansuri + w_sarangi * 0.85 * sarangi + w_sitar * 1.15 * sitar_track
    right = w_bansuri * 0.95 * bansuri + w_sarangi * 1.15 * sarangi + w_sitar * 0.85 * sitar_track

    return left, right


def synth_sitar_pluck(freq: float, dur: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Synthesize a plucked Sitar string with nonlinear Jawari (curved bridge)
    overtone buzz and frequency-dependent harmonic decay.
    """
    n = max(1, int(dur * sr))
    t = np.arange(n, dtype=np.float64) / sr

    # Slight downward pitch settling from string pluck tension
    f_t = freq * (1.0 + 0.009 * np.exp(-32.0 * t))
    phase = 2.0 * np.pi * np.cumsum(f_t) / sr

    out = np.zeros(n, dtype=np.float64)
    for h in range(1, 11):
        if freq * h >= sr * 0.44:
            break
        # Higher harmonics decay faster but shimmer with Jawari modulation
        decay_rate = 3.2 + 0.85 * h
        jawari_shimmer = 1.0 + 0.35 * np.sin(2.0 * np.pi * (1.8 + 0.4 * h) * t)
        amp = (1.0 / (h ** 0.78)) * jawari_shimmer * np.exp(-decay_rate * t)
        out += amp * np.sin(h * phase + 0.3 * h)

    # Jawari bridge grazing waveshaper
    attack = 1.0 - np.exp(-220.0 * t)
    out = np.tanh(1.65 * out) * attack
    # Fade end cleanly
    fade = min(int(0.04 * sr), n // 4)
    if fade > 1:
        out[-fade:] *= np.linspace(1.0, 0.0, fade)
    return out * 0.55


def synth_swarmandal_gliss(
    notes: List[str],
    freqs: Dict[str, float],
    sr: int = SAMPLE_RATE,
    strum_step: float = 0.055,
    ring_dur: float = 1.85,
    ascending: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Synthesize a shimmering stereo Swarmandal (Indian harp) glissando across
    the raga's scale notes.
    """
    strum_notes = list(notes) if ascending else list(reversed(notes))
    n_notes = len(strum_notes)
    total_dur = n_notes * strum_step + ring_dur
    total_samples = int(total_dur * sr)
    left = np.zeros(total_samples, dtype=np.float64)
    right = np.zeros(total_samples, dtype=np.float64)

    for i, sw in enumerate(strum_notes):
        start = int(i * strum_step * sr)
        f_hz = freqs.get(sw, 261.63)
        n_ring = min(int(ring_dur * sr), total_samples - start)
        if n_ring <= 0:
            continue
        t = np.arange(n_ring, dtype=np.float64) / sr
        env = (1.0 - np.exp(-180.0 * t)) * np.exp(-2.8 * t)
        tone = (
            np.sin(2.0 * np.pi * f_hz * t)
            + 0.45 * np.sin(4.0 * np.pi * f_hz * t + 0.4)
            + 0.20 * np.sin(6.0 * np.pi * f_hz * t + 0.9) * np.exp(-4.0 * t)
        ) * env * 0.22

        # Pan smoothly from left to right across the harp strings
        pan = i / max(1, n_notes - 1)  # 0.0 = left, 1.0 = right
        g_l = math.cos(pan * math.pi * 0.5)
        g_r = math.sin(pan * math.pi * 0.5)
        left[start:start + n_ring] += g_l * tone
        right[start:start + n_ring] += g_r * tone

    return left, right


def render(seq: List[Tuple[str, str, float]], sr: int = SAMPLE_RATE) -> np.ndarray:
    """Backwards-compatible mono sequence renderer."""
    if not seq:
        return np.zeros(int(sr * 0.5), dtype=np.float64)
    blocks = [
        synth_note(FREQUENCIES.get(note, FREQUENCIES["Sa"]), dur, sr)
        for _, note, dur in seq
    ]
    audio = np.concatenate(blocks)
    fade = min(int(sr * 0.15), len(audio) // 4)
    if fade > 1:
        audio[:fade] *= np.linspace(0.0, 1.0, fade)
        audio[-fade:] *= np.linspace(1.0, 0.0, fade)
    return audio


# ==============================================================================
# 7. TANPURA DRONE, SYMPHONIC PAD & ALAP GENERATOR
# ==============================================================================

def tanpura_drone_track(
    total_samples: int,
    freqs: Dict[str, float],
    drone_swara: str = "Pa",
    sr: int = SAMPLE_RATE,
    bpm: float = 84.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a continuous Stereo Tanpura drone (Pa/Ma - Sa' - Sa' - .Sa) with
    authentic Jivari (curved bridge) overtone shimmer.
    """
    left = np.zeros(total_samples, dtype=np.float64)
    right = np.zeros(total_samples, dtype=np.float64)

    first_string = f".{drone_swara}" if f".{drone_swara}" in freqs else drone_swara
    string_notes = [first_string, "Sa", "Sa", ".Sa"]
    string_pans = [0.25, 0.65, 0.35, 0.75]

    pluck_interval = 60.0 / max(45.0, bpm) * 1.25
    string_dur = pluck_interval * 3.8
    n_pluck = int(string_dur * sr)
    t = np.arange(n_pluck, dtype=np.float64) / sr

    # Pre-render the 4 Tanpura strings with Jivari harmonic bloom
    rendered_strings: List[Tuple[np.ndarray, float, float]] = []
    for s_idx, sw in enumerate(string_notes):
        f0 = freqs.get(sw, freqs["Sa"] * 0.5)
        wave_str = np.zeros(n_pluck, dtype=np.float64)
        for h in range(1, 9):
            if f0 * h >= sr * 0.45:
                break
            # Jivari effect: higher harmonics slowly swell in and out as string grazes the bridge
            jivari_bloom = 0.6 + 0.4 * np.sin(2.0 * np.pi * (0.35 * h) * t - 0.5 * h)
            h_amp = (1.0 / (h ** 0.85)) * jivari_bloom * np.exp(-(0.55 + 0.12 * h) * t)
            wave_str += h_amp * np.sin(2.0 * np.pi * f0 * h * t + 0.4 * h)

        attack = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, min(int(0.08 * sr), n_pluck // 4))))
        wave_str[:len(attack)] *= attack
        fade_out = np.linspace(1.0, 0.0, min(int(0.25 * sr), n_pluck // 3))
        wave_str[-len(fade_out):] *= fade_out
        wave_str /= (np.max(np.abs(wave_str)) + 1e-8)

        pan = string_pans[s_idx]
        g_l = math.cos(pan * math.pi * 0.5)
        g_r = math.sin(pan * math.pi * 0.5)
        rendered_strings.append((wave_str * 0.25, g_l, g_r))

    step_samples = max(1, int(pluck_interval * sr))
    pos = 0
    idx = 0
    while pos < total_samples:
        wave_str, g_l, g_r = rendered_strings[idx % 4]
        end = min(pos + len(wave_str), total_samples)
        seg_len = end - pos
        left[pos:end] += g_l * wave_str[:seg_len]
        right[pos:end] += g_r * wave_str[:seg_len]
        pos += step_samples
        idx += 1

    return left, right


def symphonic_pad_section(
    n_samples: int,
    raga: Dict,
    freqs: Dict[str, float],
    sr: int = SAMPLE_RATE,
    intensity: float = 0.6,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Synthesize a lush, warm stereo symphonic string & modal pad supporting
    the Raga's tonic (.Sa, Sa), fifth/fourth (.Pa/.Ma), and Vadi/Samvadi.
    """
    if n_samples <= 0:
        return np.zeros(1), np.zeros(1)

    t = np.arange(n_samples, dtype=np.float64) / sr
    drone_sw = raga.get("drone", "Pa")
    vadi_sw = raga.get("vadi", "Ga")
    # Keep Vadi in Madhya Saptak for warm pad voicing
    vadi_clean = vadi_sw.strip(". '")
    chord_swaras = [".Sa", f".{drone_sw}", "Sa", drone_sw, vadi_clean]
    chord_amps = [0.40, 0.30, 0.32, 0.24, 0.18 * intensity]

    left = np.zeros(n_samples, dtype=np.float64)
    right = np.zeros(n_samples, dtype=np.float64)

    # Slow breathing LFO
    breath_l = 0.82 + 0.18 * np.sin(2.0 * np.pi * 0.18 * t)
    breath_r = 0.82 + 0.18 * np.cos(2.0 * np.pi * 0.18 * t + 0.7)

    for sw, amp in zip(chord_swaras, chord_amps):
        f0 = freqs.get(sw, freqs["Sa"])
        # 3 detuned ensemble voices (-6 cents, 0, +6 cents)
        f_det_l = f0 * (2.0 ** (-6.0 / 1200.0))
        f_det_r = f0 * (2.0 ** (+6.0 / 1200.0))

        voice_l = (
            np.sin(2.0 * np.pi * f0 * t)
            + 0.65 * np.sin(2.0 * np.pi * f_det_l * t + 0.8)
            + 0.30 * np.sin(4.0 * np.pi * f_det_l * t + 1.5)
            + 0.12 * np.sin(6.0 * np.pi * f0 * t + 2.1)
        ) * (amp * 0.45)

        voice_r = (
            np.sin(2.0 * np.pi * f0 * t + 0.4)
            + 0.65 * np.sin(2.0 * np.pi * f_det_r * t + 1.2)
            + 0.30 * np.sin(4.0 * np.pi * f_det_r * t + 0.3)
            + 0.12 * np.sin(6.0 * np.pi * f0 * t + 1.7)
        ) * (amp * 0.45)

        left += voice_l
        right += voice_r

    left *= breath_l * intensity
    right *= breath_r * intensity

    # Smooth fade in and fade out for the section pad
    fade = min(int(0.45 * sr), n_samples // 3)
    if fade > 1:
        s_in = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, fade)))
        s_out = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, fade)))
        left[:fade] *= s_in
        right[:fade] *= s_in
        left[-fade:] *= s_out
        right[-fade:] *= s_out

    return left, right


def build_alap_intro(
    raga: Dict,
    freqs: Dict[str, float],
    bpm: float = 84.0,
    sr: int = SAMPLE_RATE,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compose a short, evocative introductory Alap (4 beats / 1 bar) with a
    cascading Swarmandal harp glissando and soulful Bansuri/Sarangi invocation
    of the Raga's Pakad before the main lyrics and Tabla enter.
    """
    beat_sec = 60.0 / max(40.0, bpm)
    pakad = raga.get("pakad", [[".Ni", "Sa", "Re", "Ga"]])[0]
    vadi = raga.get("vadi", "Ga")

    alap_swaras = [
        (".Sa" if ".Sa" in raga["notes"] else "Sa", beat_sec * 1.0),
        (pakad[0] if len(pakad) > 0 else "Sa", beat_sec * 0.75),
        (pakad[1] if len(pakad) > 1 else vadi, beat_sec * 1.0),
        ("Sa", beat_sec * 1.25),
    ]
    events = [
        NoteEvent(
            word="[Alap]",
            note=sw,
            dur=d,
            beats=d / beat_sec,
            is_rest=False,
            is_glide=True,
            has_kan=(i == 1),
            has_andolan=True,
            accent=0.82,
            sub_notes=[(sw, d)],
        )
        for i, (sw, d) in enumerate(alap_swaras)
    ]

    lead_l, lead_r = render_expressive_phrase(events, raga, freqs, sr=sr)
    n_total = len(lead_l)

    # Layer Swarmandal harp glissando at the opening of the Alap
    harp_l, harp_r = synth_swarmandal_gliss(raga.get("aaroha", raga["notes"][:7]), freqs, sr=sr)
    h_len = min(len(harp_l), n_total)
    lead_l[:h_len] += harp_l[:h_len] * 0.85
    lead_r[:h_len] += harp_r[:h_len] * 0.85

    pad_l, pad_r = symphonic_pad_section(n_total, raga, freqs, sr=sr, intensity=0.55)
    return lead_l * 0.75 + pad_l * 0.45, lead_r * 0.75 + pad_r * 0.45


# ==============================================================================
# 8. PHYSICAL-MODELING TABLA (BAYAN + TUNED DAYAN) & TALA ENGINE
# ==============================================================================

def _build_tabla_bols(tonic_hz: float = 261.63, sr: int = SAMPLE_RATE) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Synthesize realistic stereo Tabla strokes (Bayan on Left-Center, Dayan tuned
    to tonic `Sa` on Right-Center):
      - 'Ge' / 'Ghe': Resonant bass Bayan with characteristic upward-then-downward pitch meend
      - 'Na': Crisp rim stroke on Dayan tuned to Sa + 2nd/3rd harmonic ring
      - 'Tin': Sweet bell-like Maidan stroke on Dayan tuned to Sa
      - 'Tun': Open resonant Dayan stroke
      - 'Te' / 'Ti' / 'Ta' / 'Ki': Crisp damped syahi/ka strokes for Tirakita
      - 'Dha': Combined Ge (Bayan) + Na (Dayan)
      - 'Dhin': Combined Ge (Bayan) + Tin (Dayan)
    """
    rng = np.random.default_rng(108)

    # 1. Bayan 'Ge' (bass drum with pitch bend 68 Hz -> 94 Hz -> 62 Hz)
    n_ge = int(0.36 * sr)
    t_ge = np.arange(n_ge, dtype=np.float64) / sr
    f_ge = 64.0 + 30.0 * np.sin(np.pi * np.clip(t_ge / 0.22, 0.0, 1.0)) * np.exp(-5.0 * t_ge)
    ph_ge = 2.0 * np.pi * np.cumsum(f_ge) / sr
    bayan_body = (
        0.85 * np.sin(ph_ge) * np.exp(-9.5 * t_ge)
        + 0.30 * np.sin(2.0 * ph_ge + 0.4) * np.exp(-16.0 * t_ge)
    )
    bayan_thump = 0.35 * np.sin(2.0 * np.pi * 140.0 * t_ge) * np.exp(-65.0 * t_ge)
    ge_mono = (bayan_body + bayan_thump) * (1.0 - np.exp(-250.0 * t_ge))

    # 2. Dayan 'Na' (tuned to tonic Sa, bright rim overtones)
    n_na = int(0.28 * sr)
    t_na = np.arange(n_na, dtype=np.float64) / sr
    f_sa = tonic_hz
    na_ring = (
        0.55 * np.sin(2.0 * np.pi * f_sa * t_na) * np.exp(-13.0 * t_na)
        + 0.65 * np.sin(2.0 * np.pi * f_sa * 1.98 * t_na) * np.exp(-18.0 * t_na)
        + 0.35 * np.sin(2.0 * np.pi * f_sa * 2.95 * t_na) * np.exp(-28.0 * t_na)
    )
    skin_slap = rng.standard_normal(n_na) * np.exp(-140.0 * t_na) * 0.22
    na_mono = (na_ring + skin_slap) * (1.0 - np.exp(-350.0 * t_na))

    # 3. Dayan 'Tin' (sweet fundamental + 2nd harmonic Maidan bell tone)
    n_tin = int(0.32 * sr)
    t_tin = np.arange(n_tin, dtype=np.float64) / sr
    tin_ring = (
        0.85 * np.sin(2.0 * np.pi * f_sa * t_tin) * np.exp(-10.5 * t_tin)
        + 0.40 * np.sin(2.0 * np.pi * f_sa * 2.0 * t_tin) * np.exp(-16.0 * t_tin)
        + 0.15 * np.sin(2.0 * np.pi * f_sa * 1.51 * t_tin) * np.exp(-24.0 * t_tin)
    )
    tin_mono = (tin_ring + rng.standard_normal(n_tin) * np.exp(-180.0 * t_tin) * 0.12) * (1.0 - np.exp(-320.0 * t_tin))

    # 4. Damped 'Te' / 'Ti' / 'Ka' (crisp dry transient on syahi patch)
    n_te = int(0.09 * sr)
    t_te = np.arange(n_te, dtype=np.float64) / sr
    te_mono = (
        0.50 * np.sin(2.0 * np.pi * (f_sa * 0.82) * t_te) * np.exp(-55.0 * t_te)
        + 0.35 * np.sin(2.0 * np.pi * (f_sa * 1.42) * t_te) * np.exp(-75.0 * t_te)
        + 0.30 * rng.standard_normal(n_te) * np.exp(-120.0 * t_te)
    )

    n_ka = int(0.09 * sr)
    t_ka = np.arange(n_ka, dtype=np.float64) / sr
    ka_mono = (
        0.55 * np.sin(2.0 * np.pi * 105.0 * t_ka) * np.exp(-50.0 * t_ka)
        + 0.25 * rng.standard_normal(n_ka) * np.exp(-110.0 * t_ka)
    )

    # Combine into stereo bols (Bayan panned 68% Left / 32% Right; Dayan panned 32% Left / 68% Right)
    n_dha = max(n_ge, n_na)
    dha_l = np.zeros(n_dha, dtype=np.float64)
    dha_r = np.zeros(n_dha, dtype=np.float64)
    dha_l[:n_ge] += 0.72 * ge_mono
    dha_r[:n_ge] += 0.38 * ge_mono
    dha_l[:n_na] += 0.38 * na_mono
    dha_r[:n_na] += 0.72 * na_mono

    n_dhin = max(n_ge, n_tin)
    dhin_l = np.zeros(n_dhin, dtype=np.float64)
    dhin_r = np.zeros(n_dhin, dtype=np.float64)
    dhin_l[:n_ge] += 0.72 * ge_mono
    dhin_r[:n_ge] += 0.38 * ge_mono
    dhin_l[:n_tin] += 0.38 * tin_mono
    dhin_r[:n_tin] += 0.72 * tin_mono

    # High metallic Manjira / Ghungroo bell chime for Tali beats in Chorus
    n_bell = int(0.22 * sr)
    t_bell = np.arange(n_bell, dtype=np.float64) / sr
    bell_mono = (
        0.18 * np.sin(2.0 * np.pi * (f_sa * 8.0) * t_bell) * np.exp(-22.0 * t_bell)
        + 0.12 * np.sin(2.0 * np.pi * (f_sa * 11.31) * t_bell) * np.exp(-32.0 * t_bell)
    )

    return {
        "Dha":  (dha_l, dha_r),
        "Dhin": (dhin_l, dhin_r),
        "Ge":   (0.72 * ge_mono, 0.38 * ge_mono),
        "Na":   (0.38 * na_mono, 0.72 * na_mono),
        "Tin":  (0.38 * tin_mono, 0.72 * tin_mono),
        "Te":   (0.42 * te_mono, 0.68 * te_mono),
        "Ka":   (0.68 * ka_mono, 0.42 * ka_mono),
        "Bell": (0.55 * bell_mono, 0.65 * bell_mono),
    }


# Authentic Tala Theka patterns (in half-beat / eighth-note slots)
TALA_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    # Keherwa (8 beats = 16 eighth-note slots): Dha Ge Na Ti | Na Ka Dhin Na
    "Keherwa": [
        ("Dha", 1.00), ("Ge", 0.42),
        ("Ge", 0.65),  ("Te", 0.35),
        ("Na", 0.80),  ("Te", 0.35),
        ("Tin", 0.70), ("Ka", 0.40),
        ("Na", 0.85),  ("Te", 0.35),
        ("Ka", 0.65),  ("Ge", 0.45),
        ("Dhin", 0.92), ("Ge", 0.40),
        ("Na", 0.75),  ("Te", 0.38),
    ],
    # Teental (16 beats = 32 eighth-note slots): Dha Dhin Dhin Dha | Dha Dhin Dhin Dha | Dha Tin Tin Ta | Ta Dhin Dhin Dha
    "Teental": [
        ("Dha", 1.00), ("Te", 0.30), ("Dhin", 0.82), ("Ge", 0.35), ("Dhin", 0.82), ("Ge", 0.35), ("Dha", 0.88), ("Te", 0.35),
        ("Dha", 0.92), ("Te", 0.30), ("Dhin", 0.80), ("Ge", 0.35), ("Dhin", 0.80), ("Ge", 0.35), ("Dha", 0.88), ("Te", 0.35),
        ("Dha", 0.88), ("Te", 0.28), ("Tin", 0.75),  ("Te", 0.28), ("Tin", 0.75),  ("Te", 0.28), ("Na", 0.80),  ("Ka", 0.35),
        ("Na", 0.85),  ("Te", 0.32), ("Dhin", 0.85), ("Ge", 0.40), ("Dhin", 0.88), ("Ge", 0.45), ("Dha", 0.95), ("Te", 0.40),
    ],
    # Dadra (6 beats = 12 eighth-note slots): Dha Dhin Na | Dha Tin Na
    "Dadra": [
        ("Dha", 1.00), ("Ge", 0.38),
        ("Dhin", 0.85), ("Ge", 0.35),
        ("Na", 0.78),  ("Te", 0.32),
        ("Dha", 0.88), ("Ka", 0.35),
        ("Tin", 0.82), ("Te", 0.32),
        ("Na", 0.78),  ("Ge", 0.40),
    ],
    # Rupak (7 beats = 14 eighth-note slots): Tin Tin Na | Dhin Na | Dhin Na
    "Rupak": [
        ("Tin", 0.92), ("Te", 0.32),
        ("Tin", 0.80), ("Te", 0.32),
        ("Na", 0.78),  ("Ka", 0.35),
        ("Dhin", 0.90), ("Ge", 0.38),
        ("Na", 0.78),  ("Te", 0.35),
        ("Dhin", 0.90), ("Ge", 0.38),
        ("Na", 0.82),  ("Te", 0.35),
    ],
}


def tabla_track(
    total_samples: int,
    sr: int = SAMPLE_RATE,
    bpm: float = 90.0,
    tonic_hz: float = 261.63,
    tala: str = "Keherwa",
    is_chorus: bool = False,
    with_tihai: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a beat-synchronized stereo Tabla & Sub-Bass track in the specified Tala,
    including energetic Lagi variations for Choruses and a classic Tihai cadence at the end.
    (Note: If unpacked as a single array by legacy callers, `tabla_track_mono` is also available;
    here we return `(left, right)` stereo arrays.)
    """
    left = np.zeros(total_samples, dtype=np.float64)
    right = np.zeros(total_samples, dtype=np.float64)
    if total_samples <= 0:
        return left, right

    bols = _build_tabla_bols(tonic_hz=tonic_hz, sr=sr)
    pattern = TALA_PATTERNS.get(tala, TALA_PATTERNS["Keherwa"])
    n_slots = len(pattern)

    beat_sec = 60.0 / max(40.0, bpm)
    half_beat_sec = beat_sec * 0.5
    qtr_beat_sec = beat_sec * 0.25

    # Determine where the final 2 beats are so we can play a classic Tihai cadence!
    tihai_start_sample = max(0, total_samples - int(4.0 * beat_sec * sr)) if with_tihai else total_samples

    slot_idx = 0
    while True:
        pos = int(round(slot_idx * half_beat_sec * sr))
        if pos >= tihai_start_sample:
            break

        bol_name, vel = pattern[slot_idx % n_slots]
        if is_chorus:
            vel = min(1.0, vel * 1.15)

        b_l, b_r = bols[bol_name]
        end = min(pos + len(b_l), total_samples)
        seg = end - pos
        if seg > 0:
            left[pos:end] += vel * b_l[:seg]
            right[pos:end] += vel * b_r[:seg]

        # On Sam (beat 0 of cycle), add deep cinematic Mandra Saptak sub-bass pulse
        if slot_idx % n_slots == 0:
            n_sub = min(int(beat_sec * 1.2 * sr), total_samples - pos)
            if n_sub > 0:
                t_sub = np.arange(n_sub, dtype=np.float64) / sr
                sub_wave = 0.28 * np.sin(2.0 * np.pi * (tonic_hz * 0.25) * t_sub) * np.exp(-3.8 * t_sub)
                left[pos:pos + n_sub] += sub_wave
                right[pos:pos + n_sub] += sub_wave

        # In Chorus, add shimmering Manjira bell on Tali beats and Tirakita fill at cycle end
        if is_chorus and (slot_idx % 4 == 0):
            bell_l, bell_r = bols["Bell"]
            b_end = min(pos + len(bell_l), total_samples)
            if b_end > pos:
                left[pos:b_end] += 0.65 * bell_l[:b_end - pos]
                right[pos:b_end] += 0.65 * bell_r[:b_end - pos]

        if is_chorus and (slot_idx % n_slots == n_slots - 1):
            # 16th-note Tirakita fill (Te - Ka)
            off = pos + int(qtr_beat_sec * sr)
            if off < total_samples:
                tk_l, tk_r = bols["Te"]
                tk_end = min(off + len(tk_l), total_samples)
                left[off:tk_end] += 0.55 * tk_l[:tk_end - off]
                right[off:tk_end] += 0.55 * tk_r[:tk_end - off]

        slot_idx += 1

    # Render Tihai Cadence at end of section: 3x ("Ti-Ra-Ki-Ta Dha") landing on Sam!
    if with_tihai and tihai_start_sample < total_samples - int(beat_sec * sr):
        # Each of the 3 Tihai phrases is 1.25 beats (0.25*4 Tirakita + 0.25 Dha + 0.25 gap)
        pala_beats = [0.0, 1.25, 2.50]
        for p_idx, b_off in enumerate(pala_beats):
            base_pos = tihai_start_sample + int(b_off * beat_sec * sr)
            # 4 rapid sixteenth notes: Te - Ka - Te - Ka
            for sixteenth_i, b_key in enumerate(["Te", "Ka", "Te", "Ka"]):
                s_pos = base_pos + int(sixteenth_i * (beat_sec * 0.125) * sr)
                if s_pos >= total_samples:
                    break
                s_l, s_r = bols[b_key]
                s_end = min(s_pos + len(s_l), total_samples)
                left[s_pos:s_end] += 0.65 * s_l[:s_end - s_pos]
                right[s_pos:s_end] += 0.65 * s_r[:s_end - s_pos]

            # Emphatic Dha!
            dha_pos = base_pos + int(0.5 * beat_sec * sr)
            if dha_pos < total_samples:
                d_l, d_r = bols["Dha"]
                d_end = min(dha_pos + len(d_l), total_samples)
                accent = 0.90 + 0.10 * p_idx
                left[dha_pos:d_end] += accent * d_l[:d_end - dha_pos]
                right[dha_pos:d_end] += accent * d_r[:d_end - dha_pos]

    return left, right


# ==============================================================================
# 9. CONCERT HALL STEREO REVERB & STUDIO MASTERING CHAIN
# ==============================================================================

def apply_concert_hall_reverb(
    left: np.ndarray,
    right: np.ndarray,
    sr: int = SAMPLE_RATE,
    wet: float = 0.28,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply a lush Stereo Concert Hall Reverb using early reflection taps plus
    stereo cross-coupled feedback delay lines with warm high-frequency damping.
    """
    n = len(left)
    if n == 0 or wet <= 0.0:
        return left, right

    # Low-pass filter the reverb send for warm concert hall acoustics (cut harshness > 4.2 kHz)
    sos_LP = signal.butter(2, 4200.0 / (sr / 2), btype="lowpass", output="sos")
    send_l = signal.sosfilt(sos_LP, left)
    send_r = signal.sosfilt(sos_LP, right)

    rev_l = np.zeros(n, dtype=np.float64)
    rev_r = np.zeros(n, dtype=np.float64)

    # Multi-tap early reflections + diffuse late hall reflections (prime-ish ms delays)
    taps_l = [
        (0.023, 0.34), (0.041, 0.28), (0.067, 0.24), (0.097, 0.20),
        (0.139, 0.17), (0.193, 0.14), (0.263, 0.11), (0.347, 0.085),
        (0.449, 0.065), (0.577, 0.048), (0.727, 0.032), (0.911, 0.020),
    ]
    taps_r = [
        (0.029, 0.34), (0.047, 0.28), (0.073, 0.24), (0.107, 0.20),
        (0.151, 0.17), (0.211, 0.14), (0.281, 0.11), (0.367, 0.085),
        (0.479, 0.065), (0.607, 0.048), (0.761, 0.032), (0.953, 0.020),
    ]

    for delay_s, gain in taps_l:
        d = int(delay_s * sr)
        if d < n:
            rev_l[d:] += gain * (0.75 * send_l[:-d] + 0.25 * send_r[:-d])

    for delay_s, gain in taps_r:
        d = int(delay_s * sr)
        if d < n:
            rev_r[d:] += gain * (0.75 * send_r[:-d] + 0.25 * send_l[:-d])

    # Smooth the reverb tail with an allpass-like modulation / warm lowpass
    sos_tail = signal.butter(1, 3200.0 / (sr / 2), btype="lowpass", output="sos")
    rev_l = signal.sosfilt(sos_tail, rev_l)
    rev_r = signal.sosfilt(sos_tail, rev_r)

    out_l = (1.0 - wet * 0.35) * left + wet * rev_l
    out_r = (1.0 - wet * 0.35) * right + wet * rev_r
    return out_l, out_r


def master_stereo_bus(
    left: np.ndarray,
    right: np.ndarray,
    sr: int = SAMPLE_RATE,
) -> np.ndarray:
    """
    Studio mastering chain:
      1. Sub-rumble high-pass filter at 28 Hz
      2. Warm analog tape soft-saturation (`tanh`)
      3. True-peak normalization to -0.8 dBFS
      4. Returns interleaved/stacked `(N, 2)` float64 stereo array in `[-1.0, 1.0]`.
    """
    sos_hp = signal.butter(2, 28.0 / (sr / 2), btype="highpass", output="sos")
    l_clean = signal.sosfilt(sos_hp, left)
    r_clean = signal.sosfilt(sos_hp, right)

    peak_pre = max(np.max(np.abs(l_clean)), np.max(np.abs(r_clean)), 1e-8)
    l_norm = l_clean / peak_pre
    r_norm = r_clean / peak_pre

    # Gentle analog warmth saturation
    drive = 1.28
    l_sat = np.tanh(drive * l_norm) / math.tanh(drive)
    r_sat = np.tanh(drive * r_norm) / math.tanh(drive)

    # Master fade-in (150ms) and lush fade-out (1.2s)
    n = len(l_sat)
    fade_in = min(int(0.15 * sr), n // 10)
    fade_out = min(int(1.20 * sr), n // 6)
    if fade_in > 1:
        fi = np.linspace(0.0, 1.0, fade_in)
        l_sat[:fade_in] *= fi
        r_sat[:fade_in] *= fi
    if fade_out > 1:
        fo = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, fade_out)))
        l_sat[-fade_out:] *= fo
        r_sat[-fade_out:] *= fo

    peak_post = max(np.max(np.abs(l_sat)), np.max(np.abs(r_sat)), 1e-8)
    target_ceiling = 0.92  # ~ -0.7 dBFS headroom for clean MP3 encoding
    stereo = np.column_stack([l_sat, r_sat]) * (target_ceiling / peak_post)
    return stereo


# ==============================================================================
# 10. MP3 & WAV EXPORT ENGINE (LAMEENC + FFMPEG FALLBACK)
# ==============================================================================

def export_audio_to_mp3(
    stereo_audio: np.ndarray,
    output_path: str | Path,
    sr: int = SAMPLE_RATE,
    bitrate: int = 320,
    also_save_wav: bool = False,
) -> Path:
    """
    Encode a stereo (N, 2) or mono (N,) float array in [-1, 1] into a high-bitrate
    320 kbps Stereo MP3 file using `lameenc` (or `ffmpeg` fallback).
    """
    out_path = Path(output_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if stereo_audio.ndim == 1:
        stereo_audio = np.column_stack([stereo_audio, stereo_audio])

    pcm16 = np.clip(stereo_audio * 32767.0, -32768, 32767).astype(np.int16)
    pcm_bytes = pcm16.tobytes()

    if also_save_wav or out_path.suffix.lower() == ".wav":
        wav_path = out_path if out_path.suffix.lower() == ".wav" else out_path.with_suffix(".wav")
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_bytes)
        if out_path.suffix.lower() == ".wav":
            return wav_path

    # Primary encoder: lameenc (fast, zero-subprocess C extension)
    try:
        import lameenc
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bitrate)
        encoder.set_in_sample_rate(sr)
        encoder.set_channels(2)
        encoder.set_quality(2)  # 2 = highest studio quality in LAME
        mp3_data = encoder.encode(pcm_bytes) + encoder.flush()
        out_path.write_bytes(mp3_data)
        return out_path
    except Exception:
        pass

    # Fallback encoder: ffmpeg
    ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    tmp_wav = out_path.with_suffix(".tmp.wav")
    try:
        with wave.open(str(tmp_wav), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_bytes)
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(tmp_wav), "-codec:a", "libmp3lame", "-b:a", f"{bitrate}k", str(out_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        if tmp_wav.exists():
            tmp_wav.unlink()

    return out_path


# ==============================================================================
# 11. MAIN PIPELINE: SONG TO OSCAR-EDITION MUSIC
# ==============================================================================

def song_to_music(
    raw_lyrics: str,
    output_mp3: str | Path = "output_music.mp3",
    bpm: int = 84,
    melody_vol: float = 0.82,
    tabla_vol: float = 0.34,
    drone_vol: float = 0.24,
    pad_vol: float = 0.30,
    tonic: str = "C#",
    forced_raga: Optional[str] = None,
    forced_tala: Optional[str] = None,
    include_alap: bool = True,
    also_save_wav: bool = False,
    sr: int = SAMPLE_RATE,
) -> Path:
    """
    Full end-to-end pipeline:
      1. Parses song into structured sections & poetic lines.
      2. Analyzes Navarasa emotion per section & assigns Raga + Tala.
      3. Composes beat-synchronized melody with motif memory, Pakad phrases,
         and multi-syllable melismas (Swara Vistara).
      4. Synthesizes Alap intro, continuous-phase Bansuri/Sarangi/Sitar lead,
         Swarmandal harp glissandi, Symphonic String Pad, Stereo Tanpura Drone,
         and tonic-tuned Stereo Tabla with Tihai cadences.
      5. Applies Concert Hall Stereo Reverb & studio mastering, and saves MP3.
    """
    global FREQUENCIES
    tonic_hz = TONIC_FREQUENCIES.get(tonic, 277.18)
    FREQUENCIES = build_frequency_map(tonic_hz)

    sections = parse_song(raw_lyrics)
    motif_cache: Dict[str, List[NoteEvent]] = {}

    if RICH_AVAILABLE and console is not None:
        console.print(
            Panel.fit(
                f"[bold gold1]🎼 RasAI — Navarasa Symphonic Raga Engine[/bold gold1]\n"
                f"[cyan]Sections:[/cyan] {len(sections)} ({', '.join(s['label'] for s in sections)})   "
                f"[cyan]Tonic (Sa):[/cyan] {tonic} ({tonic_hz:.2f} Hz)   "
                f"[cyan]BPM:[/cyan] {bpm}",
                border_style="gold1",
            )
        )
    else:
        print(f"\n🎼  {len(sections)} section(s): {[s['label'] for s in sections]} | Tonic: {tonic} ({tonic_hz:.2f} Hz) | BPM: {bpm}\n")

    full_left: List[np.ndarray] = []
    full_right: List[np.ndarray] = []
    all_seq: List[Tuple[str, str, str, List[NoteEvent]]] = []

    # Primary Raga from first section used for introductory Alap & global drone
    first_raga_name, first_raga = pick_raga(sections[0]["text"], sections[0]["label"], forced_raga=forced_raga)

    if include_alap:
        alap_l, alap_r = build_alap_intro(first_raga, FREQUENCIES, bpm=bpm, sr=sr)
        full_left.append(alap_l * melody_vol)
        full_right.append(alap_r * melody_vol)

    for sec_i, sec in enumerate(sections):
        legacy_seq, events, raga_name, raga = build_sequence(
            sec,
            bpm=bpm,
            forced_raga=forced_raga,
            motif_cache=motif_cache,
        )
        tala_name = forced_tala if (forced_tala in TALA_PATTERNS) else raga.get("default_tala", "Keherwa")
        lbl_lower = sec["label"].lower()
        is_chorus = "chorus" in lbl_lower or "hook" in lbl_lower or "refrain" in lbl_lower
        is_bridge = "bridge" in lbl_lower

        if RICH_AVAILABLE and console is not None:
            console.print(
                f"  [bold magenta][{sec['label']}][/bold magenta]  "
                f"Raga: [bold yellow]{raga_name}[/bold yellow]  |  "
                f"Rasa: [italic green]{raga['rasa']}[/italic green]  |  "
                f"Tala: [cyan]{tala_name}[/cyan]"
            )
        else:
            print(f"  [{sec['label']}]  raga: {raga_name}  mood: {raga['mood']}  tala: {tala_name}")

        # 1. Expressive Lead (Bansuri + Sarangi + Sitar Jawari plucks)
        lead_l, lead_r = render_expressive_phrase(events, raga, FREQUENCIES, sr=sr)
        n_sec = len(lead_l)

        # 2. Swarmandal Harp Glissando at Chorus / Bridge entrances
        if is_chorus or is_bridge or sec_i == len(sections) - 1:
            harp_l, harp_r = synth_swarmandal_gliss(
                raga.get("aaroha", raga["notes"][:7]),
                FREQUENCIES,
                sr=sr,
                ascending=(not is_bridge),
            )
            h_len = min(len(harp_l), n_sec)
            lead_l[:h_len] += harp_l[:h_len] * 0.70
            lead_r[:h_len] += harp_r[:h_len] * 0.70

        # 3. Symphonic String Pad (swells during Chorus & Bridge)
        pad_intensity = 0.85 if is_chorus else (0.75 if is_bridge else 0.52)
        pad_l, pad_r = symphonic_pad_section(n_sec, raga, FREQUENCIES, sr=sr, intensity=pad_intensity)

        # 4. Beat-Synchronized Stereo Tabla & Sub-Bass with Tihai cadence
        tab_l, tab_r = tabla_track(
            n_sec,
            sr=sr,
            bpm=bpm,
            tonic_hz=tonic_hz,
            tala=tala_name,
            is_chorus=is_chorus,
            with_tihai=True,
        )

        sec_l = melody_vol * lead_l + pad_vol * pad_l + tabla_vol * tab_l
        sec_r = melody_vol * lead_r + pad_vol * pad_r + tabla_vol * tab_r

        full_left.append(sec_l)
        full_right.append(sec_r)
        all_seq.append((sec["label"], raga_name, tala_name, events))

    # Add a final resolving Shadja (Sa) chord + Swarmandal outro tail (2 beats)
    outro_samples = int((60.0 / max(40.0, bpm)) * 2.5 * sr)
    outro_pad_l, outro_pad_r = symphonic_pad_section(outro_samples, first_raga, FREQUENCIES, sr=sr, intensity=0.65)
    harp_out_l, harp_out_r = synth_swarmandal_gliss(first_raga.get("aaroha", first_raga["notes"][:7]), FREQUENCIES, sr=sr)
    ho_len = min(len(harp_out_l), outro_samples)
    outro_pad_l[:ho_len] += harp_out_l[:ho_len] * 0.65
    outro_pad_r[:ho_len] += harp_out_r[:ho_len] * 0.65
    full_left.append(outro_pad_l * pad_vol)
    full_right.append(outro_pad_r * pad_vol)

    mix_l = np.concatenate(full_left)
    mix_r = np.concatenate(full_right)

    # 5. Continuous Stereo Tanpura Drone with Jivari shimmer across the whole piece
    drone_swara = first_raga.get("drone", "Pa")
    tan_l, tan_r = tanpura_drone_track(len(mix_l), FREQUENCIES, drone_swara=drone_swara, sr=sr, bpm=bpm)
    mix_l += drone_vol * tan_l
    mix_r += drone_vol * tan_r

    # 6. Concert Hall Stereo Reverb & Studio Mastering
    wet_l, wet_r = apply_concert_hall_reverb(mix_l, mix_r, sr=sr, wet=0.28)
    master_stereo = master_stereo_bus(wet_l, wet_r, sr=sr)

    # Print detailed Word -> Swara -> Melisma -> Duration table
    _print_score_table(all_seq)

    out_file = export_audio_to_mp3(
        master_stereo,
        output_mp3,
        sr=sr,
        bitrate=320,
        also_save_wav=also_save_wav,
    )

    duration_sec = len(master_stereo) / sr
    if RICH_AVAILABLE and console is not None:
        console.print(
            Panel.fit(
                f"[bold green]✅ Mastered MP3 Saved![/bold green]\n"
                f"📁 [bold white]{out_file}[/bold white]\n"
                f"⏱️  Duration: [cyan]{duration_sec:.1f}s[/cyan]  |  "
                f"🎚️  Format: [cyan]44.1 kHz Stereo 320 kbps MP3[/cyan]",
                border_style="green",
            )
        )
    else:
        print(f"\n🎵  Duration: {duration_sec:.1f}s | BPM: {bpm}")
        print(f"✅  Saved MP3 to: {out_file}\n")

    # If executed inside an IPython/Jupyter notebook, also display the audio player
    try:
        from IPython import get_ipython
        if get_ipython() is not None:
            from IPython.display import Audio, display
            display(Audio(master_stereo.T, rate=sr, autoplay=False))
    except Exception:
        pass

    return out_file


def _print_score_table(all_seq: List[Tuple[str, str, str, List[NoteEvent]]]) -> None:
    """Display the musical score mapping words to Swaras, Melismas, and Beat durations."""
    if RICH_AVAILABLE and console is not None:
        table = Table(title="🎼 Musical Score (Word → Swara Vistara → Duration)", box=box.SIMPLE_HEAVY)
        table.add_column("Section", style="bold magenta", no_wrap=True)
        table.add_column("Raga", style="yellow", no_wrap=True)
        table.add_column("Word", style="white", no_wrap=True)
        table.add_column("Swara / Melisma", style="bold cyan", no_wrap=True)
        table.add_column("Articulation", style="green")
        table.add_column("Dur (s)", justify="right", style="bright_white", no_wrap=True)

        for label, raga_name, _tala, events in all_seq:
            first_row = True
            for ev in events:
                if ev.is_rest:
                    continue
                swara_str = " → ".join(sw for sw, _ in ev.sub_notes) if len(ev.sub_notes) > 1 else ev.note
                arts = []
                if len(ev.sub_notes) > 1 or ev.is_glide:
                    arts.append("Meend")
                if ev.has_kan:
                    arts.append("Kan")
                if ev.has_andolan:
                    arts.append("Andolan")
                table.add_row(
                    label if first_row else "",
                    raga_name if first_row else "",
                    ev.word,
                    swara_str,
                    ", ".join(arts) if arts else "Shuddha",
                    f"{ev.dur:.2f}s",
                )
                first_row = False
        console.print(table)
    else:
        print(f"\n{'─' * 68}")
        print(f"{'SECTION':<13} {'RAGA':<13} {'WORD':<16} {'SWARA VISTARA':<16} {'DUR':>6}")
        print("─" * 68)
        for label, raga_name, _tala, events in all_seq:
            sec_lbl, rg_lbl = label, raga_name
            for ev in events:
                if ev.is_rest:
                    continue
                swara_str = "->".join(sw for sw, _ in ev.sub_notes) if len(ev.sub_notes) > 1 else ev.note
                print(f"{sec_lbl:<13} {rg_lbl:<13} {ev.word:<16} {swara_str:<16} {ev.dur:>5.2f}s")
                sec_lbl, rg_lbl = "", ""
        print("─" * 68)


# ==============================================================================
# 12. DEFAULT DEMO SONG & COMMAND-LINE INTERFACE
# ==============================================================================

DEFAULT_SONG = """[Verse 1]
In the stillness of the morning
I hear the river calling me
Beneath the ancient banyan shadow
My heart finds what it needs to be

[Chorus]
Oh take me home take me home
Where the mountains meet the sea
Let the wind carry my sorrow
And bring me back to me

[Bridge]
There is no darkness without light
No silence without song
Every parting every sadness
Means somewhere I belong

[Chorus]
Oh take me home take me home
Where the mountains meet the sea
Let the wind carry my sorrow
And bring me back to me
"""


def resolve_input_lyrics(args: argparse.Namespace) -> str:
    """
    Read lyrics from:
      1. `--file` / `-f` text file path
      2. `--lyrics` / `-l` raw text string
      3. Positional `input` (automatically detects if it's a file path or raw lyrics text)
      4. Piped `sys.stdin` or interactive terminal prompt (falls back to DEFAULT_SONG if empty)
    """
    if args.file:
        p = Path(args.file).expanduser()
        if not p.is_file():
            sys.exit(f"Error: Lyrics file not found: {p}")
        return p.read_text(encoding="utf-8")

    if args.lyrics:
        return args.lyrics.replace("\\n", "\n")

    if args.input:
        candidate = Path(args.input).expanduser()
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
        return args.input.replace("\\n", "\n")

    # Check if stdin is piped
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            return piped

    if args.demo:
        return DEFAULT_SONG

    # Interactive prompt when run in terminal with no arguments
    print("🎤 Paste or type your lyrics below.")
    print("   (Type 'END' on a new line and press Enter, or press Enter on an empty first line to run the demo song):")
    lines: List[str] = []
    try:
        while True:
            line = input()
            if not lines and line.strip() == "":
                print("✨ Using built-in demo song...")
                return DEFAULT_SONG
            if line.strip().upper() == "END":
                break
            lines.append(line)
    except EOFError:
        pass

    text = "\n".join(lines).strip()
    return text if text else DEFAULT_SONG


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RasAI — Convert song lyrics (from CLI text or a .txt file) into an Oscar-worthy Indian Classical & Cinematic MP3.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. From a text file:
  python lyrics_to_music.py sample_lyrics.txt -o my_song.mp3

  # 2. Directly typed on the command line:
  python lyrics_to_music.py "In the stillness of the morning\\nI hear the river calling me" -o morning.mp3

  # 3. With explicit Raga, Tala, Tonic, and BPM:
  python lyrics_to_music.py -f sample_lyrics.txt -o yaman_song.mp3 --raga Yaman --tala Teental --tonic D --bpm 88

  # 4. Run the built-in multi-section demo song:
  python lyrics_to_music.py --demo -o oscar_demo.mp3
""",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to a lyrics .txt file OR raw lyrics text string.",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        default=None,
        help="Path to a text file containing the song lyrics.",
    )
    parser.add_argument(
        "-l", "--lyrics",
        type=str,
        default=None,
        help="Raw lyrics text passed directly via command line.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output_music.mp3",
        help="Output MP3 file path (default: output_music.mp3).",
    )
    parser.add_argument(
        "--bpm",
        type=int,
        default=84,
        help="Tempo in Beats Per Minute (default: 84).",
    )
    parser.add_argument(
        "--tonic",
        type=str,
        default="C#",
        choices=sorted(TONIC_FREQUENCIES.keys()),
        help="Concert tonic pitch for Sa (default: C# = 277.18 Hz).",
    )
    parser.add_argument(
        "--raga",
        type=str,
        default=None,
        choices=sorted(RAGAS.keys()),
        help="Force a specific Raga (default: automatic Navarasa emotional selection per section).",
    )
    parser.add_argument(
        "--tala",
        type=str,
        default=None,
        choices=sorted(TALA_PATTERNS.keys()),
        help="Force a specific Tala rhythm cycle (default: auto-matched to Raga).",
    )
    parser.add_argument(
        "--melody-vol",
        type=float,
        default=0.82,
        help="Lead melody volume 0.0-1.0 (default: 0.82).",
    )
    parser.add_argument(
        "--tabla-vol",
        type=float,
        default=0.34,
        help="Tabla & percussion volume 0.0-1.0 (default: 0.34).",
    )
    parser.add_argument(
        "--drone-vol",
        type=float,
        default=0.24,
        help="Tanpura drone volume 0.0-1.0 (default: 0.24).",
    )
    parser.add_argument(
        "--pad-vol",
        type=float,
        default=0.30,
        help="Symphonic string pad volume 0.0-1.0 (default: 0.30).",
    )
    parser.add_argument(
        "--no-alap",
        action="store_true",
        help="Disable the introductory Alap before the first section.",
    )
    parser.add_argument(
        "--wav",
        action="store_true",
        help="Also save an uncompressed .wav file alongside the .mp3.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run immediately using the built-in 4-section song.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    lyrics_text = resolve_input_lyrics(args)

    song_to_music(
        raw_lyrics=lyrics_text,
        output_mp3=args.output,
        bpm=args.bpm,
        melody_vol=args.melody_vol,
        tabla_vol=args.tabla_vol,
        drone_vol=args.drone_vol,
        pad_vol=args.pad_vol,
        tonic=args.tonic,
        forced_raga=args.raga,
        forced_tala=args.tala,
        include_alap=not args.no_alap,
        also_save_wav=args.wav,
    )


if __name__ == "__main__":
    main()
