#!/usr/bin/env python3
"""A tiny Essentia "hello world" example.

Usage:
  python scripts/essentia_hello.py [path/to/audio.wav]

If no audio path is provided the script synthesizes a short sine
test tone and analyzes that.

This script prints:
 - Essentia version
 - Audio duration and sample rate
 - Tempo estimate and first few beat timestamps
 - A single-frame spectral centroid (as an example spectral
   feature)

It intentionally keeps dependencies light and prints a helpful
install message when Essentia is not available.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from typing import Optional


def _extract_rhythm(audio, es_module):
    """Run RhythmExtractor2013 and return a tolerant tuple:
    (tempo: float, beats: list[float], beats_confidence: Optional[float], extras: list)
    """
    re = es_module.RhythmExtractor2013(method="multifeature")
    res = re(audio)

    tempo = float(res[0]) if len(res) > 0 else 0.0
    beats = list(map(float, res[1])) if len(res) > 1 else []
    beats_confidence = None
    if len(res) > 2 and isinstance(res[2], (float, int)):
        beats_confidence = float(res[2])
    extras = list(res[3:]) if len(res) > 3 else []
    return tempo, beats, beats_confidence, extras


def _load_audio(audio_path: Optional[str], es_module):
    """Load an audio file using Essentia or synthesize a short test tone.

    Returns tuple: (audio, sr, temp_file_or_none)
    """
    if audio_path and os.path.exists(audio_path):
        loader = es_module.MonoLoader(filename=audio_path)
        audio = loader()
        sr = 44100
        print(f"Loaded audio: {audio_path}")
        return audio, sr, None

    # synthesize a short 2s 440Hz test tone and return a temp filename used to load it
    import numpy as np
    import soundfile as sf

    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.3 * np.sin(2.0 * np.pi * 440.0 * t)

    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file = tf.name
    tf.close()
    sf.write(temp_file, tone.astype("float32"), sr)

    loader = es_module.MonoLoader(filename=temp_file)
    audio = loader()
    print("No audio file specified — synthesized 2s 440Hz test tone.")
    return audio, sr, temp_file


def _compute_centroid(audio, sr, es_module) -> float:
    WINDOW_SIZE = 2048
    frame = audio[:WINDOW_SIZE]
    if len(frame) < WINDOW_SIZE:
        import numpy as _np

        frame = _np.pad(frame, (0, WINDOW_SIZE - len(frame)))

    window = es_module.Windowing(type="hann")
    spectrum = es_module.Spectrum(size=WINDOW_SIZE)
    centroid = es_module.Centroid(range=float(sr) / 2.0)

    w = window(frame)
    s = spectrum(w)
    return float(centroid(s))


def _print_essentia_version(es_module) -> None:
    try:
        import essentia

        print("Essentia version:", essentia.__version__)
    except Exception:
        v = getattr(es_module, "__version__", None)
        if v:
            print("Essentia version:", v)


def main():
    try:
        import essentia.standard as es
    except Exception as exc:  # ImportError / other failures
        print("Essentia import failed — not installed or failed to load.")
        print()
        print("Install options:")
        print("  - Conda (recommended): use the provided environment file (see docs)")
        print("  - Example (mamba):")
        print(
            "      mamba create -n songshare-essentia -c conda-forge "
            "python=3.11 essentia"
        )
        print("  - Or: pip install essentia (if a compatible wheel exists)")
        print()
        print("See docs/essentia-integration.md for full setup instructions.")
        print()
        print("Original error:", repr(exc))
        raise SystemExit(1) from exc

    parser = argparse.ArgumentParser(
        description="Essentia hello-world analyzer",
    )
    parser.add_argument(
        "audio",
        nargs="?",
        help="Optional path to an audio file (wav/mp3/...).",
    )
    args = parser.parse_args()

    audio_path = args.audio

    temp_file: Optional[str] = None

    try:
        audio, sr, temp_file = _load_audio(audio_path, es)

        # duration
        duration_seconds = float(len(audio)) / float(sr)
        print(f"Duration: {duration_seconds:.3f} s, Sample rate (assumed): {sr}")

        # Rhythm extraction (tempo + beats)
        try:
            tempo, beats, beats_confidence, extras = _extract_rhythm(audio, es)
            print(f"Tempo (bpm): {tempo:.2f}")
            print(f"Beats (first 8): {beats[:8]}")
            print(f"Beats confidence: {beats_confidence}")
            if extras:
                print(f"Extra rhythm outputs present (count={len(extras)}).")
        except Exception as e:
            print("RhythmExtractor not available or failed:", repr(e))

        # Spectral centroid example (single-frame on the first frame)
        try:
            c = _compute_centroid(audio, sr, es)
            print(f"Spectral centroid (first frame): {c:.2f} Hz")
        except Exception as exc:
            print("Spectral centroid extraction failed:", repr(exc))

        # Essentia version (print if available)
        _print_essentia_version(es)

    finally:
        if temp_file:
            try:
                os.unlink(temp_file)
            except Exception:
                pass


if __name__ == "__main__":
    main()
