# Essentia Hello World

A minimal example showing how to run Essentia to extract a few basic features.

Path: `scripts/essentia_hello.py`

Usage:

```bash
# analyze an existing audio file
python scripts/essentia_hello.py path/to/file.wav

# synthesize a short test tone and analyze it
python scripts/essentia_hello.py
```

What it prints:

- Essentia version
- Audio duration (seconds)
- Tempo estimate (bpm) and a small list of beat timestamps
- A sample spectral centroid value (Hz)

Example output (synthesized tone):

```
No audio file specified — synthesized 2s 440Hz test tone.
Duration: 2.000 s, Sample rate (assumed): 44100
Tempo (bpm): 0.00
Beats (first 8): []
Beats confidence: 0.0
Spectral centroid (first frame): 440.00 Hz
Essentia version: 2.1
```

Notes:

- The script prints a helpful message if Essentia is not installed and points to `docs/essentia-integration.md` for install instructions.
- The script synthesizes a test tone when no audio path is provided to allow quick local verification without external fixtures.

