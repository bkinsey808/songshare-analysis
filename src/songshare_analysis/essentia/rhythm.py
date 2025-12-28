"""Essentia-related rhythm helpers.

This module contains rhythm timing detection helpers that operate on Essentia
outputs (beat timestamps) as well as small utilities to write ID3 TXXX frames
and write analysis sidecars.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, Sequence

import numpy as np

# Mutagen ID3 writer (third-party; type ignored for environments without stubs)
from mutagen.id3 import ID3, TXXX, ID3NoHeaderError  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    # Provide type information for static checkers when Essentia stubs are present
    try:
        from essentia.standard import MusicExtractor  # type: ignore
    except Exception:  # pragma: no cover - stubs may be missing
        MusicExtractor = Any  # type: ignore


def detect_rhythm_timing_from_beats(
    beats: Sequence[float],
    subdivisions: int = 16,
    quant_tol_sec: float = 0.01,
    min_beats: int = 8,
) -> Dict[str, Any]:
    """Determine rhythm timing label and confidence from beat timestamps.

    Returns a dict containing the following keys:
    - label, confidence, reason, bpm, beat_cv, quant_score, n_beats
    """
    beats_arr = np.asarray(list(beats), dtype=float)

    if len(beats_arr) < min_beats:
        return {
            "label": "uncertain",
            "confidence": 0.0,
            "reason": "too_few_beats",
            "bpm": None,
            "beat_cv": None,
            "quant_score": None,
            "n_beats": int(len(beats_arr)),
        }

    ibis = np.diff(beats_arr)
    mean_ibi = float(np.mean(ibis))
    mad = float(np.median(np.abs(ibis - np.median(ibis))))
    robust_std = 1.4826 * mad
    cv = robust_std / mean_ibi if mean_ibi > 0 else float("inf")

    # quantization score
    beat_period = mean_ibi
    phases = np.mod(beats_arr, beat_period) / beat_period
    grids = np.arange(subdivisions) / float(subdivisions)
    # compute fractional distance to nearest grid point
    frac_dist = np.minimum.reduce([np.abs(phases - g) for g in grids])
    frac_dist = np.minimum(frac_dist, 1 - frac_dist)
    sec_dist = frac_dist * beat_period
    quant_score = float(np.mean(sec_dist <= quant_tol_sec))

    # map CV to score in [0..1] (lower CV => higher score)
    # we clamp using a sensible range where 0.0..0.02 maps to 1..0
    cv_score = max(0.0, (0.02 - cv) / 0.02)
    combined = 0.6 * cv_score + 0.4 * quant_score
    confidence = float(np.clip(combined, 0.0, 1.0))

    if confidence >= 0.6:
        label = "clicktrack"
    elif confidence <= 0.4:
        label = "human"
    else:
        label = "uncertain"

    reason = f"cv={cv:.5f},quant={quant_score:.3f}"
    bpm = 60.0 / mean_ibi if mean_ibi > 0 else None

    return {
        "label": label,
        "confidence": confidence,
        "reason": reason,
        "bpm": float(bpm) if bpm is not None else None,
        "beat_cv": float(cv),
        "quant_score": float(quant_score),
        "n_beats": int(len(beats)),
    }


def detect_rhythm_timing(
    path: str,
    subdivisions: int = 16,
    quant_tol_sec: float = 0.01,
    min_beats: int = 8,
) -> Dict[str, Any]:
    """Extract beats using Essentia and call the beat-based detector.

    Raises RuntimeError if Essentia is not installed or extraction fails.
    """
    try:
        import importlib  # dynamic import to avoid hard dependency at

        # module import time

        ess = importlib.import_module("essentia.standard")
        MusicExtractor = ess.MusicExtractor
    except Exception as err:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "Essentia is required for detect_rhythm_timing(path) but is not available"
        ) from err

    extractor = MusicExtractor()
    features, _ = extractor(path)
    beats = features.get("rhythm.beats", [])
    return detect_rhythm_timing_from_beats(
        beats=beats,
        subdivisions=subdivisions,
        quant_tol_sec=quant_tol_sec,
        min_beats=min_beats,
    )


def write_rhythm_id3_tags(mp3_path: str, analysis: Dict[str, Any]) -> None:
    """Write custom TXXX tags for rhythm timing.

    - TXXX:rhythm_human -> confidence (string)
    - TXXX:rhythm_machine -> confidence (string)
    - TXXX:rhythm_timing -> label
    - TXXX:rhythm_timing_confidence -> numeric string 0..1
    - TXXX:rhythm_timing_reason -> short reason

    The function will create ID3 header if missing.
    """
    label = analysis.get("label")
    confidence = analysis.get("confidence", 0.0)
    reason = analysis.get("reason", "")
    beat_cv = analysis.get("beat_cv")
    quant = analysis.get("quant_score")

    try:
        id3 = ID3(mp3_path)
    except ID3NoHeaderError:
        id3 = ID3()

    # set TXXX frames
    # human/machine presence frames - numeric confidence as string
    human_val = f"{confidence:.6f}" if label == "human" else "0"
    machine_val = f"{confidence:.6f}" if label == "clicktrack" else "0"

    id3.delall("TXXX:rhythm_human")
    id3.add(TXXX(encoding=3, desc="rhythm_human", text=human_val))
    id3.delall("TXXX:rhythm_machine")
    id3.add(TXXX(encoding=3, desc="rhythm_machine", text=machine_val))

    id3.delall("TXXX:rhythm_timing")
    id3.add(TXXX(encoding=3, desc="rhythm_timing", text=str(label)))
    id3.delall("TXXX:rhythm_timing_confidence")
    id3.add(TXXX(encoding=3, desc="rhythm_timing_confidence", text=f"{confidence:.6f}"))
    if reason:
        id3.delall("TXXX:rhythm_timing_reason")
        id3.add(TXXX(encoding=3, desc="rhythm_timing_reason", text=str(reason)))

    # optional: add beat_cv and quant_score frames if present
    if beat_cv is not None:
        id3.delall("TXXX:beat_cv")
        id3.add(TXXX(encoding=3, desc="beat_cv", text=f"{beat_cv:.6f}"))
    if quant is not None:
        id3.delall("TXXX:quant_score")
        id3.add(TXXX(encoding=3, desc="quant_score", text=f"{quant:.6f}"))

    # save
    id3.save(mp3_path)


def write_analysis_sidecar(mp3_path: str, analysis: Dict[str, Any]) -> str:
    """Write analysis JSON sidecar next to mp3 (e.g., song.mp3.analysis.json).

    Returns the path to the sidecar file.
    """
    sidecar_path = f"{mp3_path}.analysis.json"
    with open(sidecar_path, "w", encoding="utf-8") as fh:
        json.dump(analysis, fh, indent=2, sort_keys=True)
    return sidecar_path
