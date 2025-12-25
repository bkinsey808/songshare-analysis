from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = getLogger(__name__)


class PannsNotInstalled(RuntimeError):
    pass


def _import_panns() -> Any:
    """Return a compatible tagger class from `panns_inference`.

    Some releases expose `SoundTagging` while others provide `AudioTagging`.
    Accept either and return a class with a compatible `inference` API.
    """
    try:
        # Try historical name first for compatibility with tests and older
        # releases that expose `SoundTagging`.
        from panns_inference import SoundTagging  # type: ignore

        return SoundTagging
    except Exception:
        # Newer releases expose `AudioTagging` instead; accept that as well.
        try:
            from panns_inference import AudioTagging  # type: ignore

            return AudioTagging
        except Exception as exc:  # pragma: no cover - optional dependency
            msg = (
                "PANNs (panns-inference) is not installed or failed to import. "
                "Install with: pip install panns-inference torch librosa soundfile"
            )
            raise PannsNotInstalled(msg) from exc


def _detect_best_device() -> str:
    """Detect best available device for PANNs.

    Currently PANNs should use CPU-only PyTorch in this project, so this
    function forces the device to 'cpu' until GPU/XPU support is re-enabled.
    """
    # Temporarily force CPU to avoid GPU dependencies in tests and CI.
    # TODO: Re-enable GPU/XPU detection when the runtime environment supports it.
    return "cpu"


def infer_genre_panns(
    audio_path: Path, device: str | None = None, top_k: int = 3
) -> Dict[str, Any]:
    """Run PANNs tagger on an audio file and return a normalized genre dict.

    The `device` argument may be `'cuda'`, `'cpu'`, `'xpu:0'` or `None` (or `'auto'`).
    If `None` or `'auto'` the function will attempt to use Intel XPU (if available),
    then CUDA, otherwise CPU.

    This wrapper tolerates a couple of output shapes from `panns_inference` and
    normalizes them to the following dict:

    {
        "provenance": {"model": "panns-inference", "version": <str|None>},
        "labels": [...],
        "probs": [...],
        "probs_dict": {label: prob, ...},
        "top": <label or None>,
        "top_confidence": <float>,
        "top_k": [(label, prob), ...]
    }

    Raises PannsNotInstalled with installation instructions if dependency missing.
    """
    SoundTagging = _import_panns()

    model = SoundTagging(device=device)

    # call inference - panns_inference historically accepted a file path,
    # but some releases expect a waveform array instead. Try path first and
    # fall back to loading the waveform with librosa if necessary.
    try:
        res = model.inference(str(audio_path))
    except Exception:
        # Try loading audio into a waveform array and call inference again.
        try:
            import librosa  # type: ignore
            import numpy as np  # type: ignore

            waveform, _ = librosa.load(str(audio_path), sr=32000, mono=True)
            arr = np.array([waveform], dtype=float)
            res = model.inference(arr)
        except Exception:
            logger.exception("PANNs inference failed for %s", str(audio_path))
            raise

    # Normalize output into labels/probs using a small helper that keeps the
    # complexity of this function low and handles multiple panns return shapes.
    labels, probs = _normalize_panns_output(res, model)

    probs_dict = dict(zip(labels, probs, strict=True))

    sorted_labels: List[Tuple[str, float]] = sorted(
        probs_dict.items(), key=lambda x: x[1], reverse=True
    )
    top_label, top_conf = sorted_labels[0] if sorted_labels else (None, 0.0)

    return {
        "provenance": {
            "model": "panns-inference",
            "version": getattr(model, "__version__", None),
        },
        "labels": labels,
        "probs": probs,
        "probs_dict": probs_dict,
        "top": top_label,
        "top_confidence": float(top_conf) if top_conf is not None else 0.0,
        "top_k": sorted_labels[:top_k],
    }


def _from_labels_probs_dict(r: dict) -> tuple[list[str], list[float]] | None:
    if "labels" in r and "probs" in r:
        labels = list(r.get("labels", []))
        probs = [float(p) for p in r.get("probs", [])]
        return labels, probs
    return None


def _from_probs_dict(r: dict) -> tuple[list[str], list[float]] | None:
    if "probs_dict" in r:
        probs_dict = r.get("probs_dict", {}) or {}
        labels = list(probs_dict.keys())
        probs = [float(probs_dict[k]) for k in labels]
        return labels, probs
    return None


def _from_clipwise_array(arr: Any, model: Any) -> tuple[list[str], list[float]] | None:
    try:
        import numpy as np  # type: ignore

        if isinstance(arr, np.ndarray) and hasattr(model, "labels"):
            if getattr(arr, "ndim", 0) > 1 and arr.shape[0] == 1:
                arr = arr[0]
            if getattr(arr, "ndim", 0) == 1:
                labels = list(model.labels)
                probs = [float(x) for x in arr]
                return labels, probs
    except Exception:
        return None
    return None


def _normalize_panns_output(res: Any, model: Any) -> tuple[list[str], list[float]]:
    """Normalize different PANNs return formats into (labels, probs)."""

    # Dict shaped outputs
    if isinstance(res, dict):
        v = _from_labels_probs_dict(res)
        if v:
            return v
        v = _from_probs_dict(res)
        if v:
            return v
        # clipwise_output: numpy array of shape (num_labels,)
        if "clipwise_output" in res:
            v = _from_clipwise_array(res.get("clipwise_output"), model)
            if v:
                return v

    # tuple/list outputs like (clipwise_output, embedding)
    if isinstance(res, (tuple, list)):
        v = _from_clipwise_array(res[0], model)
        if v:
            return v

    raise RuntimeError("Unexpected PANNs inference output format")
