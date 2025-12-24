from __future__ import annotations

from contextlib import contextmanager
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@contextmanager
def _suppress_essentia_info():
    """Temporarily raise Essentia's logger to WARNING to suppress noisy info
    messages (for example: "MusicExtractorSVM: no classifier models were
    configured by default") which can be emitted during `MusicExtractor`
    construction or extraction. Restores previous levels afterward."""
    log = logging.getLogger("essentia")
    prev = log.level
    try:
        log.setLevel(logging.WARNING)
        yield
    finally:
        log.setLevel(prev)


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


def _call_music_extractor(me_obj, audio_in):
    try:
        try:
            return me_obj(audio_in)
        except Exception:
            return me_obj.extract(audio_in)
    except Exception:
        return None


def _compute_hpcp_chroma(es, audio_in):
    try:
        w = es.Windowing(type="hann")(audio_in[:2048])
        s = es.Spectrum(size=2048)(w)
        h = es.HPCP(size=12)(s)

        total = float(sum(h)) or 1.0
        labels = [
            "C",
            "C#",
            "D",
            "D#",
            "E",
            "F",
            "F#",
            "G",
            "G#",
            "A",
            "A#",
            "B",
        ]
        chroma = {lab: float(v) / total for lab, v in zip(labels, h, strict=True)}
        return chroma
    except Exception:
        return {}


def _try_tuning(es, audio_in):
    if not hasattr(es, "TuningFrequency"):
        return None
    try:
        tf = es.TuningFrequency()(audio_in)
        return {"reference_hz": float(tf)}
    except Exception:
        return None


def extract_tonal(audio_path: Path) -> dict:
    """Compact tonal extraction summary: key, key_strength, chroma histogram,
    mfcc summary (mean/std), and tuning hint. Returns a dict suitable for the
    sidecar (conservative; None where data couldn't be computed).
    """
    essentia, es = _essentia_import()

    loader = es.MonoLoader(filename=str(audio_path))
    audio = loader()

    key = None
    key_strength = None
    chroma_hist: dict = {}
    mfcc_mean: list[float] = []
    mfcc_std: list[float] = []
    tuning: dict | None = None

    try:
        if hasattr(es, "MusicExtractor"):
            with _suppress_essentia_info():
                me = es.MusicExtractor()
                pool = _call_music_extractor(me, audio)
            if pool is not None:
                key = pool.get("tonal.key") or pool.get("tonal.key_technical")
                key_strength = pool.get("tonal.key_strength")
                mfcc_mean = list(pool.get("mfcc.mean", [])) or list(
                    pool.get("tonal.mfcc.mean", [])
                )
                mfcc_std = list(pool.get("mfcc.std", [])) or list(
                    pool.get("tonal.mfcc.std", [])
                )
                chroma_hist = pool.get("tonal.chroma_histogram") or {}

        if not chroma_hist and hasattr(es, "HPCP"):
            chroma_hist = _compute_hpcp_chroma(es, audio)

        tuning = _try_tuning(es, audio)

    except Exception:  # pragma: no cover - environment dependent
        key = None
        key_strength = None
        chroma_hist = {}
        mfcc_mean = []
        mfcc_std = []
        tuning = None

    return {
        "tonal": {"key": key, "key_strength": key_strength},
        "chroma": chroma_hist,
        "mfcc": {"mean": mfcc_mean, "std": mfcc_std},
        "tuning": tuning,
    }


def extract_sections(audio_path: Path) -> dict:
    """Return a compact list of sections. This is intentionally lightweight
    and will return a single full-track section if a more advanced method is
    unavailable on the platform.
    """
    essentia, es = _essentia_import()

    loader = es.MonoLoader(filename=str(audio_path))
    audio = loader()

    sections: list[dict] = []

    try:
        # Try to use a segmentation algorithm if available
        if hasattr(es, "Segmentation"):
            try:
                seg = es.Segmentation()
                segs = seg(audio)
                # Transform into start/end segments if seg produces boundaries
                for s in segs:
                    # Expect s to be numeric timestamps or tuples
                    if isinstance(s, (list, tuple)) and len(s) >= 2:
                        sections.append({"start": float(s[0]), "end": float(s[1])})
            except Exception:
                sections = []

        if not sections:
            # Fallback: single section covering whole file using rough sr=44100
            duration = float(len(audio)) / 44100.0 if len(audio) > 0 else 0.0
            sections = [{"start": 0.0, "end": duration, "label": "full"}]
    except Exception:
        sections = [{"start": 0.0, "end": 0.0, "label": "unknown"}]

    return {"sections": sections}


def extract_semantic(audio_path: Path) -> dict:
    """Run model-based semantic classifiers (genre, mood, instruments).

    Currently attempts PANNs (preferred) and falls back to Essentia's
    `MusicExtractor` model outputs when available. Returns a dict suitable
    for merging into the analysis sidecar under the `semantic` key.
    """
    # Try PANNs first (preferred multi-label tagger)
    try:
        from songshare_analysis.genre.panns import infer_genre_panns  # type: ignore

        try:
            res = infer_genre_panns(audio_path)
            return {"semantic": {"genre": res}}
        except Exception:
            # If inference failed, fall through to MusicExtractor
            pass
    except Exception:
        # panns not installed; fall back to MusicExtractor below
        pass

    # Fallback: Essentia MusicExtractor (if available and yields genre fields)
    try:
        essentia, es = _essentia_import()
        if hasattr(es, "MusicExtractor"):
            with _suppress_essentia_info():
                me = es.MusicExtractor()
                pool = _call_music_extractor(me, audio_path)
            if pool is not None:
                genre_top = pool.get("genre.top") or pool.get("genre")
                top_conf = pool.get("genre.top_confidence") or pool.get(
                    "genre_confidence", None
                )
                if genre_top:
                    # MusicExtractor may not provide full probs; wrap minimal
                    genre_dict = {
                        "provenance": {
                            "model": "essentia_music_extractor",
                            "version": getattr(essentia, "__version__", None),
                        },
                        "top": genre_top,
                        "top_confidence": (
                            float(top_conf) if top_conf is not None else 0.0
                        ),
                    }
                    return {"semantic": {"genre": genre_dict}}
    except Exception:
        pass

    # Nothing available
    return {"semantic": {"genre": {}}}


def _freq_to_midi(freq: float) -> int:
    import math

    if freq <= 0:
        return 0
    return int(round(69 + 12 * math.log2(freq / 440.0)))


def _midi_to_note(m: int) -> str:
    names = [
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "A#",
        "B",
    ]
    octave = m // 12 - 1
    name = names[m % 12]
    return f"{name}{octave}"


def extract_vocals(vocals_path: Path) -> dict:
    """Analyze an already-separated vocals stem (or a full mix if provided).

    Returns a compact summary with vocal presence (0-1), and pitch summary
    (median_midi, median_note) when determinable.
    """
    essentia, es = _essentia_import()

    loader = es.MonoLoader(filename=str(vocals_path))
    audio = loader()

    presence = None
    median_midi = None
    median_note = None

    try:
        # Predominant melody / pitch extractor if available
        if hasattr(es, "PredominantPitchMelodia"):
            try:
                ppm = es.PredominantPitchMelodia()
                pitch, _ = ppm(audio)
                # pitch: array of floats (Hz) with 0 for unvoiced
                voiced = [float(p) for p in pitch if p and p > 0.0]
                presence = float(len(voiced)) / (len(pitch) or 1)
                if voiced:
                    # median
                    import statistics

                    med = statistics.median(voiced)
                    midi = _freq_to_midi(med)
                    median_midi = midi
                    median_note = _midi_to_note(midi)
            except Exception:
                presence = None
        else:
            # Fallback: no pitch extractor; set presence None
            presence = None
    except Exception:
        presence = None

    return {
        "vocals": {
            "presence": presence,
            "median_midi": median_midi,
            "median_note": median_note,
        }
    }


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
