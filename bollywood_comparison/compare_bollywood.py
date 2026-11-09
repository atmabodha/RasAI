#!/usr/bin/env python3
"""
Download 5 classic Indian-classical-based Bollywood songs, run lyrics_to_music.py
on their lyrics (both Auto mode and Raga-Matched mode), and perform a deep
DSP, acoustic, prosodic, and musicological comparison.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy import signal

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import lyrics_to_music as ltm

COMP_DIR = Path(__file__).resolve().parent
LYRICS_DIR = COMP_DIR / "lyrics"
ORIG_DIR = COMP_DIR / "original_mp3"
GEN_DIR = COMP_DIR / "generated_mp3"

ORIG_DIR.mkdir(parents=True, exist_ok=True)
GEN_DIR.mkdir(parents=True, exist_ok=True)

SONGS = [
    {
        "id": "01_abhi_na_jao_chhod_kar",
        "title": "Abhi Na Jao Chhod Kar",
        "movie": "Hum Dono (1961)",
        "composer": "Jaidev",
        "lyricist": "Sahir Ludhianvi",
        "singer": "Mohammed Rafi & Asha Bhosle",
        "true_raga": "Yaman",
        "true_tala": "Dadra",
        "true_tonic": "C#",
        "true_bpm": 88,
        "itunes_query": "Abhi Na Jao Chhod Kar Asha Bhosle Mohd Rafi",
        "lyrics_file": LYRICS_DIR / "01_abhi_na_jao_chhod_kar.txt",
    },
    {
        "id": "02_o_duniya_ke_rakhwale",
        "title": "O Duniya Ke Rakhwale",
        "movie": "Baiju Bawra (1952)",
        "composer": "Naushad",
        "lyricist": "Shakeel Badayuni",
        "singer": "Mohammed Rafi",
        "true_raga": "Darbari",
        "true_tala": "Keherwa",
        "true_tonic": "D",
        "true_bpm": 76,
        "itunes_query": "O Duniya Ke Rakhwale Mohd Rafi",
        "lyrics_file": LYRICS_DIR / "02_o_duniya_ke_rakhwale.txt",
    },
    {
        "id": "03_jago_mohan_pyare",
        "title": "Jago Mohan Pyare",
        "movie": "Jagte Raho (1956)",
        "composer": "Salil Chowdhury",
        "lyricist": "Shailendra",
        "singer": "Lata Mangeshkar",
        "true_raga": "Bhairav",
        "true_tala": "Dadra",
        "true_tonic": "C#",
        "true_bpm": 92,
        "itunes_query": "Jago Mohan Pyare Lata Mangeshkar",
        "lyrics_file": LYRICS_DIR / "03_jago_mohan_pyare.txt",
    },
    {
        "id": "04_mere_naina_sawan_bhadon",
        "title": "Mere Naina Sawan Bhadon",
        "movie": "Mehbooba (1976)",
        "composer": "R. D. Burman",
        "lyricist": "Anand Bakshi",
        "singer": "Kishore Kumar",
        "true_raga": "Shivaranjani",
        "true_tala": "Keherwa",
        "true_tonic": "D#",
        "true_bpm": 82,
        "itunes_query": "Mere Naina Sawan Bhadon Kishore Kumar",
        "lyrics_file": LYRICS_DIR / "04_mere_naina_sawan_bhadon.txt",
    },
    {
        "id": "05_laga_chunari_mein_daag",
        "title": "Laga Chunari Mein Daag",
        "movie": "Dil Hi To Hai (1963)",
        "composer": "Roshan",
        "lyricist": "Sahir Ludhianvi",
        "singer": "Manna Dey",
        "true_raga": "Bhairavi",
        "true_tala": "Teental",
        "true_tonic": "D",
        "true_bpm": 108,
        "itunes_query": "Laga Chunari Mein Daag Manna Dey",
        "lyrics_file": LYRICS_DIR / "05_laga_chunari_mein_daag.txt",
    },
]

FFMPEG_BIN = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"


def download_original_mp3(song: Dict) -> Tuple[Path, Path]:
    """Download the reference track via iTunes API and transcode to 44.1kHz stereo MP3 + WAV."""
    mp3_path = ORIG_DIR / f"{song['id']}_original.mp3"
    wav_path = ORIG_DIR / f"{song['id']}_original.wav"
    m4a_tmp = ORIG_DIR / f"{song['id']}_tmp.m4a"

    if mp3_path.exists() and wav_path.exists():
        return mp3_path, wav_path

    url = (
        "https://itunes.apple.com/search?term="
        + urllib.parse.quote(song["itunes_query"])
        + "&media=music&entity=song&limit=3"
    )
    req = urllib.request.urlopen(url, timeout=15)
    data = json.loads(req.read().decode("utf-8"))
    results = data.get("results", [])
    if not results:
        raise RuntimeError(f"No preview found for {song['title']}")

    preview_url = results[0]["previewUrl"]
    print(f"⬇️  Downloading original track: {song['title']} ({results[0].get('artistName')})...")
    urllib.request.urlretrieve(preview_url, m4a_tmp)

    subprocess.run(
        [
            FFMPEG_BIN, "-y", "-i", str(m4a_tmp),
            "-ar", "44100", "-ac", "2", "-codec:a", "libmp3lame", "-b:a", "320k",
            str(mp3_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            FFMPEG_BIN, "-y", "-i", str(m4a_tmp),
            "-ar", "44100", "-ac", "2",
            str(wav_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if m4a_tmp.exists():
        m4a_tmp.unlink()
    return mp3_path, wav_path


def load_wav_stereo(wav_path: Path) -> Tuple[np.ndarray, int]:
    """Load 16-bit PCM stereo WAV into float64 array of shape (N, 2) in [-1, 1]."""
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    if n_ch == 2:
        pcm = pcm.reshape(-1, 2)
    else:
        pcm = np.column_stack([pcm, pcm])
    return pcm, sr


def analyze_audio_features(wav_path: Path) -> Dict[str, float]:
    """Extract DSP, spectral, dynamic, stereo, rhythmic, and pitch contour metrics."""
    stereo, sr = load_wav_stereo(wav_path)
    mono = 0.5 * (stereo[:, 0] + stereo[:, 1])
    side = 0.5 * (stereo[:, 0] - stereo[:, 1])
    n = len(mono)
    dur_sec = n / sr

    # 1. Dynamic & Stereo metrics
    rms_total = float(np.sqrt(np.mean(mono ** 2) + 1e-12))
    peak = float(np.max(np.abs(stereo)) + 1e-12)
    crest_db = float(20.0 * np.log10(peak / rms_total))

    # Frame-level RMS (50ms hop) for dynamic expression range
    hop = int(0.05 * sr)
    win = int(0.10 * sr)
    rms_frames = []
    for start in range(0, n - win, hop):
        frame = mono[start:start + win]
        r = np.sqrt(np.mean(frame ** 2) + 1e-12)
        if r > 1e-4:
            rms_frames.append(20.0 * np.log10(r))
    rms_db_std = float(np.std(rms_frames)) if rms_frames else 0.0
    rms_db_p95_p10 = float(np.percentile(rms_frames, 95) - np.percentile(rms_frames, 10)) if rms_frames else 0.0

    # Stereo width (Side/Mid energy ratio)
    mid_energy = float(np.mean(mono ** 2) + 1e-12)
    side_energy = float(np.mean(side ** 2) + 1e-12)
    stereo_width_ratio = float(np.sqrt(side_energy / mid_energy))

    # 2. Spectral band energy distribution & Spectral Centroid
    f, Pxx = signal.welch(mono, fs=sr, nperseg=4096)
    total_power = float(np.sum(Pxx) + 1e-12)

    def band_pct(f_lo: float, f_hi: float) -> float:
        mask = (f >= f_lo) & (f < f_hi)
        return float(100.0 * np.sum(Pxx[mask]) / total_power)

    sub_bass_pct = band_pct(20.0, 120.0)
    low_mid_pct = band_pct(120.0, 500.0)
    vocal_lead_pct = band_pct(500.0, 3500.0)
    presence_pct = band_pct(3500.0, 8000.0)
    air_pct = band_pct(8000.0, 20000.0)

    spectral_centroid_hz = float(np.sum(f * Pxx) / total_power)
    geom_mean = float(np.exp(np.mean(np.log(Pxx + 1e-15))))
    arith_mean = float(np.mean(Pxx + 1e-15))
    spectral_flatness = float(geom_mean / arith_mean)

    # 3. Pitch / Melodic f0 tracking in lead vocal/instrument band (140 Hz - 1100 Hz)
    sos_lead = signal.butter(2, [140.0 / (sr / 2), 1100.0 / (sr / 2)], btype="bandpass", output="sos")
    lead_sig = signal.sosfilt(sos_lead, mono)
    p_win = int(0.045 * sr)
    p_hop = int(0.020 * sr)
    f0_track = []
    min_lag = int(sr / 1000.0)
    max_lag = int(sr / 140.0)

    for start in range(0, min(n - p_win, int(30.0 * sr)), p_hop):
        seg = lead_sig[start:start + p_win]
        if np.sqrt(np.mean(seg ** 2)) < rms_total * 0.25:
            continue
        seg = seg - np.mean(seg)
        corr = np.correlate(seg, seg, mode="full")[p_win - 1:]
        corr /= (corr[0] + 1e-12)
        search = corr[min_lag:max_lag]
        if len(search) == 0:
            continue
        best_idx = int(np.argmax(search))
        if search[best_idx] > 0.45:
            lag = min_lag + best_idx
            f0_track.append(sr / lag)

    if len(f0_track) > 5:
        f0_arr = np.array(f0_track)
        cents = 1200.0 * np.log2(f0_arr / np.median(f0_arr))
        pitch_span_semitones = float((np.percentile(cents, 95) - np.percentile(cents, 5)) / 100.0)
        pitch_std_semitones = float(np.std(cents) / 100.0)
        # Frame-to-frame pitch movement (glides/vibrato/ornamentation)
        dcents = np.abs(np.diff(cents))
        micro_movement = float(np.median(dcents[dcents < 300.0])) if np.any(dcents < 300.0) else 0.0
    else:
        pitch_span_semitones = 0.0
        pitch_std_semitones = 0.0
        micro_movement = 0.0

    # 4. Rhythmic Onset Density
    env = np.abs(signal.hilbert(lead_sig[:min(n, int(30.0 * sr))]))
    env_smooth = signal.sosfilt(signal.butter(2, 15.0 / (sr / 2), btype="lowpass", output="sos"), env)
    onset_diff = np.maximum(0.0, np.diff(env_smooth))
    peaks, _ = signal.find_peaks(
        onset_diff,
        distance=int(0.14 * sr),
        height=np.mean(onset_diff) + 0.85 * np.std(onset_diff),
    )
    analyzed_dur = min(dur_sec, 30.0)
    onset_rate_per_sec = float(len(peaks) / max(1.0, analyzed_dur))

    return {
        "duration_sec": round(dur_sec, 2),
        "crest_factor_db": round(crest_db, 2),
        "dynamic_range_p95_p10_db": round(rms_db_p95_p10, 2),
        "rms_db_std": round(rms_db_std, 2),
        "stereo_width_ratio": round(stereo_width_ratio, 3),
        "sub_bass_20_120_pct": round(sub_bass_pct, 2),
        "low_mid_120_500_pct": round(low_mid_pct, 2),
        "vocal_lead_500_3500_pct": round(vocal_lead_pct, 2),
        "presence_3500_8000_pct": round(presence_pct, 2),
        "air_8000_20000_pct": round(air_pct, 2),
        "spectral_centroid_hz": round(spectral_centroid_hz, 1),
        "spectral_flatness": round(spectral_flatness, 5),
        "pitch_span_semitones": round(pitch_span_semitones, 2),
        "pitch_std_semitones": round(pitch_std_semitones, 2),
        "frame_pitch_mod_cents": round(micro_movement, 2),
        "onset_rate_per_sec": round(onset_rate_per_sec, 2),
    }


def analyze_lyrics_pipeline_behavior(song: Dict) -> Dict:
    """Inspect how lyrics_to_music.py parses, scores sentiment, counts syllables, and assigns Ragas."""
    raw_text = song["lyrics_file"].read_text(encoding="utf-8")
    sections = ltm.parse_song(raw_text)

    sec_reports = []
    all_words = []
    syllable_mismatches = []

    for sec in sections:
        rasa_scores = ltm.analyze_rasa(sec["text"], sec["label"])
        auto_raga, raga_dict = ltm.pick_raga(sec["text"], sec["label"], forced_raga=None)
        sec_reports.append({
            "label": sec["label"],
            "auto_raga": auto_raga,
            "auto_tala": raga_dict.get("default_tala"),
            "rasa_scores": {k: round(v, 3) for k, v in rasa_scores.items()},
        })
        for w in sec["text"].split():
            clean = w.lower().strip(",.!?")
            all_words.append(clean)
            if clean.endswith("e") and len(clean) > 3 and not clean.endswith("ee"):
                syllable_mismatches.append((clean, ltm.syllables(clean)))

    return {
        "sections": sec_reports,
        "silent_e_Hindi_words": syllable_mismatches[:8],
    }


def main() -> None:
    summary_report = []

    for song in SONGS:
        print("=" * 72)
        print(f"🎬 Processing: {song['title']} ({song['movie']}) — True Raga: {song['true_raga']}")
        orig_mp3, orig_wav = download_original_mp3(song)

        raw_lyrics = song["lyrics_file"].read_text(encoding="utf-8")

        # 1. Run lyrics_to_music.py in AUTO mode (default CLI behavior)
        auto_mp3 = GEN_DIR / f"{song['id']}_rasai_auto.mp3"
        auto_wav = GEN_DIR / f"{song['id']}_rasai_auto.wav"
        ltm.song_to_music(
            raw_lyrics=raw_lyrics,
            output_mp3=auto_mp3,
            also_save_wav=True,
        )

        # 2. Run lyrics_to_music.py in RAGA-MATCHED mode (true Raga, Tala, Tonic, BPM)
        matched_mp3 = GEN_DIR / f"{song['id']}_rasai_matched.mp3"
        matched_wav = GEN_DIR / f"{song['id']}_rasai_matched.wav"
        ltm.song_to_music(
            raw_lyrics=raw_lyrics,
            output_mp3=matched_mp3,
            bpm=song["true_bpm"],
            tonic=song["true_tonic"],
            forced_raga=song["true_raga"],
            forced_tala=song["true_tala"],
            also_save_wav=True,
        )

        orig_feats = analyze_audio_features(orig_wav)
        auto_feats = analyze_audio_features(auto_wav)
        matched_feats = analyze_audio_features(matched_wav)
        pipeline_diag = analyze_lyrics_pipeline_behavior(song)

        summary_report.append({
            "song": {k: str(v) for k, v in song.items()},
            "original_mp3": str(orig_mp3),
            "rasai_auto_mp3": str(auto_mp3),
            "rasai_matched_mp3": str(matched_mp3),
            "pipeline_diagnostics": pipeline_diag,
            "metrics_original": orig_feats,
            "metrics_rasai_auto": auto_feats,
            "metrics_rasai_matched": matched_feats,
        })

    report_json = COMP_DIR / "comparison_metrics.json"
    report_json.write_text(json.dumps(summary_report, indent=2), encoding="utf-8")
    print(f"\n✅ Saved full comparison metrics to: {report_json}")


if __name__ == "__main__":
    main()
