from __future__ import annotations

import json
from typing import Any

DEFAULT_THRESHOLDS = {
    "confidence": 0.6,
    "tuning": 0.7,
}


def analysis_to_id3(
    analysis: dict[str, Any], thresholds: dict | None = None
) -> dict[str, str]:
    """Convert a compact analysis dict into an ID3 tag mapping.

    This follows the conservative write rules: only write scalars with sufficient
    confidence and store provenance in `TXXX:provenance`.
    """
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    out: dict[str, str] = {}

    prov = analysis.get("provenance") or {}
    try:
        out["TXXX:provenance"] = json.dumps(prov, separators=",", ensure_ascii=False)
    except Exception:
        out["TXXX:provenance"] = str(prov)

    a = analysis.get("analysis") or {}
    rhythm = a.get("rhythm") or {}
    tonal = a.get("tonal") or {}

    bpm = rhythm.get("bpm")
    if isinstance(bpm, (int, float)):
        out["TBPM"] = str(float(bpm))

    key = tonal.get("key")
    key_strength = tonal.get("key_strength")
    if isinstance(key, str):
        if key_strength is None or float(key_strength) >= th["confidence"]:
            out["TKEY"] = key

    # Add tuning/pitch info if present and confident
    tuning = a.get("tuning") or {}
    if tuning:
        cents = tuning.get("cents_offset")
        ref = tuning.get("reference_hz")
        if cents is not None:
            out["TXXX:tuning_cents"] = str(cents)
        if ref is not None:
            out["TXXX:tuning_ref_hz"] = str(ref)

    # Semantic -> Genre mapping
    semantic = analysis.get("semantic") or {}
    genre = semantic.get("genre") or {}

    top = genre.get("top")
    top_conf = genre.get("top_confidence")

    def _genre_confident(conf):
        if conf is None:
            return True
        try:
            return float(conf) >= th["confidence"]
        except Exception:
            return False

    if top and _genre_confident(top_conf):
        out["TCON"] = str(top)
        try:
            out["TXXX:genre_top_confidence"] = str(float(top_conf))
        except Exception:
            pass

        top_k = genre.get("top_k")
        if top_k:
            try:
                out["TXXX:genre_top_k"] = json.dumps(top_k, ensure_ascii=False)
            except Exception:
                out["TXXX:genre_top_k"] = str(top_k)

    return out
