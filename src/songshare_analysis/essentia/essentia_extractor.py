from __future__ import annotations

import json
from logging import getLogger
from pathlib import Path
from typing import Any

logger = getLogger(__name__)


def _essentia_import() -> Any:
    try:
        # Imported lazily to avoid hard runtime dependency for users who don't
        # use Essentia; silence static analysis when types are not available.
        import essentia  # type: ignore[reportMissingImports]
        import essentia.standard as es  # type: ignore[reportMissingImports]

        return essentia, es
    except Exception as exc:  # pragma: no cover - runtime dep
        msg = (
            "Essentia is not installed or failed to import. "
            "Install via conda-forge or see docs/essentia-integration.md"
        )
        raise RuntimeError(msg) from exc


def extract_basic(audio_path: Path) -> dict:
    """Run a minimal Essentia extraction (bpm, beats, centroid) and return a
    dictionary formatted for the JSON sidecar.

    This function is intentionally conservative and returns a compact summary
    rather than full per-frame matrices.
    """
    essentia, es = _essentia_import()

    loader = es.MonoLoader(filename=str(audio_path))
    audio = loader()

    # Rhythm
    try:
        re = es.RhythmExtractor2013(method="multifeature")
        res = re(audio)
        bpm = float(res[0]) if len(res) > 0 else None
        beats = list(map(float, res[1])) if len(res) > 1 else []
        beat_conf = float(res[2]) if len(res) > 2 else None
    except Exception:
        bpm = None
        beats = []
        beat_conf = None

    # Tuning/centroid example
    try:
        centroid = None
        c = es.Centroid(range=float(44100) / 2.0)
        windowed = es.Windowing(type="hann")(audio[:2048])
        spectrum = es.Spectrum(size=2048)(windowed)
        centroid = float(c(spectrum))
    except Exception:
        centroid = None

    analysis = {
        "version": "0.1",
        "provenance": {
            "tool": "essentia",
            "version": getattr(essentia, "__version__", None),
        },
        "analysis": {
            "rhythm": {"bpm": bpm, "beats": beats, "beat_cv": beat_conf},
            "spectral": {"centroid": centroid},
        },
    }
    return analysis


def write_analysis_sidecar(audio_path: Path, analysis: dict) -> Path:
    """Write `analysis` to a JSON sidecar next to `audio_path`.

    Returns the path to the sidecar file.
    """
    sidecar = audio_path.with_suffix(audio_path.suffix + ".analysis.json")
    try:
        with sidecar.open("w", encoding="utf8") as f:
            json.dump(analysis, f, indent=2)
    except Exception:
        logger.exception("Failed to write analysis sidecar: %s", str(sidecar))
        raise
    return sidecar


def read_sidecar(audio_path: Path) -> dict | None:
    sidecar = audio_path.with_suffix(audio_path.suffix + ".analysis.json")
    if not sidecar.exists():
        return None
    try:
        with sidecar.open("r", encoding="utf8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Failed to read analysis sidecar: %s", str(sidecar))
        return None
