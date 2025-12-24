from __future__ import annotations

import json
from typing import Any

DEFAULT_THRESHOLDS = {
    "confidence": 0.6,
    "tuning": 0.7,
}


def _write_basic_tags(out: dict, analysis_block: dict, th: dict) -> None:
    rhythm = analysis_block.get("rhythm") or {}
    tonal = analysis_block.get("tonal") or {}

    bpm = rhythm.get("bpm")
    if isinstance(bpm, (int, float)):
        out["TBPM"] = str(float(bpm))

    key = tonal.get("key")
    key_strength = tonal.get("key_strength")
    if isinstance(key, str) and (
        key_strength is None or float(key_strength) >= th["confidence"]
    ):
        out["TKEY"] = key

    # Add tuning/pitch info if present and confident
    tuning = analysis_block.get("tuning") or {}
    if tuning:
        cents = tuning.get("cents_offset")
        ref = tuning.get("reference_hz")
        if cents is not None:
            out["TXXX:tuning_cents"] = str(cents)
        if ref is not None:
            out["TXXX:tuning_ref_hz"] = str(ref)


def _write_genre_core(out: dict, genre: dict, th: dict) -> bool:
    """Write core genre tags (TCON and genre_top_* TXXXs).

    Returns True if we wrote a core TCON value, False otherwise.
    """
    top = genre.get("top")
    top_conf = genre.get("top_confidence")

    def _genre_confident(conf):
        if conf is None:
            return True
        try:
            return float(conf) >= th["confidence"]
        except Exception:
            return False

    def _is_genre_label(label: str) -> bool:
        if not isinstance(label, str):
            return False
        lb = label.strip().lower()
        GENERIC_BLACKLIST = {
            "music",
            "song",
            "singing",
            "speech",
            "vocal music",
            "background music",
            "music for children",
            "soundtrack music",
            "audio",
            "instrumental",
            "music video",
        }
        return lb not in GENERIC_BLACKLIST

    if top and _genre_confident(top_conf) and _is_genre_label(top):
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
        return True

    # No core genre written
    return False


def _emit_panns_labels(out: dict, genre: dict) -> None:
    probs_dict = genre.get("probs_dict")
    if not probs_dict:
        labels = genre.get("labels") or []
        probs = genre.get("probs") or []
        if labels and probs and len(labels) == len(probs):
            probs_dict = dict(zip(labels, probs, strict=True))

    if not isinstance(probs_dict, dict) or not probs_dict:
        return

    try:
        import bisect

        sorted_probs = sorted(float(x) for x in probs_dict.values())
        n = len(sorted_probs)
        for label, prob in sorted(
            probs_dict.items(), key=lambda x: float(x[1]), reverse=True
        ):
            try:
                p = float(prob)
            except Exception:
                continue
            if n <= 1:
                decile = 0
            else:
                rank = bisect.bisect_right(sorted_probs, p) - 1
                decile = int(rank * 10 / n)
                if decile < 0:
                    decile = 0
                if decile > 9:
                    decile = 9
            key = f"TXXX:panns {label}"
            out[key] = str(decile)
    except Exception:
        return


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
    _write_basic_tags(out, a, th)

    # Semantic -> Genre mapping
    semantic = analysis.get("semantic") or {}
    genre = semantic.get("genre") or {}

    written_core = _write_genre_core(out, genre, th)

    if isinstance(genre, dict) and genre and written_core:
        # If we wrote a core genre value, also emit PANNs per-label frames
        _emit_panns_labels(out, genre)
    else:
        # Always write provenance and raw semantic data for downstream
        # inspection even when conservative rules prevented TCON from being set.
        top = genre.get("top")
        top_conf = genre.get("top_confidence")
        if top:
            try:
                out["TXXX:genre_top"] = str(top)
            except Exception:
                pass
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


def compute_panns_deciles(genre: dict) -> list[dict]:
    """Return a list of per-label decile info computed from a PANNs genre dict.

    Each entry is a dict with keys: `label`, `prob`, and `decile`. The list is
    sorted by probability descending so it's convenient to inspect top labels.
    """
    probs_dict = genre.get("probs_dict")
    if not probs_dict:
        labels = genre.get("labels") or []
        probs = genre.get("probs") or []
        if labels and probs and len(labels) == len(probs):
            probs_dict = dict(zip(labels, probs, strict=True))

    if not isinstance(probs_dict, dict) or not probs_dict:
        return []

    try:
        import bisect

        sorted_probs = sorted(float(x) for x in probs_dict.values())
        n = len(sorted_probs)
        rows: list[dict] = []
        for label, prob in sorted(
            probs_dict.items(), key=lambda x: float(x[1]), reverse=True
        ):
            try:
                p = float(prob)
            except Exception:
                continue
            if n <= 1:
                decile = 0
            else:
                rank = bisect.bisect_right(sorted_probs, p) - 1
                decile = int(rank * 10 / n)
                if decile < 0:
                    decile = 0
                if decile > 9:
                    decile = 9
            rows.append({"label": label, "prob": p, "decile": decile})
        return rows
    except Exception:
        return []
