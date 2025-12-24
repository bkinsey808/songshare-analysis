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

    def _is_genre_label(label: str) -> bool:
        """Return True if `label` looks like a real music genre rather than
        a broad descriptor (e.g., "Music", "Song", "Singing", "Speech").

        This is intentionally conservative: we blacklist common generic labels
        and otherwise allow the label to be written. The list can be extended
        in future or replaced by a configurable whitelist.
        """
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

    # Emit decile-ranked PANNs tags for each label so callers can inspect
    # per-label confidence at a coarse granularity. Use `probs_dict` when
    # available (full set of label probabilities) otherwise fall back to
    # `labels`/`probs` pairs when present.
    probs_dict = genre.get("probs_dict")
    if not probs_dict:
        labels = genre.get("labels") or []
        probs = genre.get("probs") or []
        if labels and probs and len(labels) == len(probs):
            probs_dict = dict(zip(labels, probs, strict=True))

    if isinstance(probs_dict, dict) and probs_dict:
        try:
            import bisect

            # Precompute sorted probs ascending for decile computation
            sorted_probs = sorted(float(x) for x in probs_dict.values())
            n = len(sorted_probs)
            # Iterate labels sorted by probability descending so insertion order
            # in the output dict reflects highest-first ordering.
            for label, prob in sorted(
                probs_dict.items(),
                key=lambda x: float(x[1]),
                reverse=True,
            ):
                try:
                    p = float(prob)
                except Exception:
                    continue
                if n <= 1:
                    decile = 0
                else:
                    # rank: index of this value in the ascending sorted list (0..n-1)
                    rank = bisect.bisect_right(sorted_probs, p) - 1
                    decile = int(rank * 10 / n)
                    if decile < 0:
                        decile = 0
                    if decile > 9:
                        decile = 9
                key = f"TXXX:panns {decile} {label}"
                try:
                    out[key] = str(float(p))
                except Exception:
                    out[key] = str(p)
        except Exception:
            # Non-fatal: if something goes wrong generating panns tags, skip
            pass

    else:
        # Always write provenance and raw semantic data even when we do not
        # apply a conservative `TCON` value so downstream inspection/debugging
        # can see what models produced. We write raw top/top_confidence/top_k
        # into TXXX fields when we choose not to set the core TCON frame.
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
