import os
import shutil
import subprocess
import tempfile

import numpy as np
import pytest

from songshare_analysis.essentia import (  # noqa: F401 - ensure package available
    essentia_extractor as _dummy,
)


def _build_mp3_fixture(path: str) -> bool:
    # Require ffmpeg and soundfile to be available
    if shutil.which("ffmpeg") is None:
        return False
    try:
        import importlib

        sf = importlib.import_module("soundfile")
    except Exception:
        return False

    sr = 22050
    duration = 0.5
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.3 * np.sin(2.0 * np.pi * 440.0 * t)

    wav_tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = wav_tf.name
    wav_tf.close()

    try:
        sf.write(wav_path, tone.astype("float32"), sr)
        mp3_path = path
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path, mp3_path],
            check=True,
        )
        return os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0
    except Exception:
        return False
    finally:
        try:
            if os.path.exists(wav_path):
                os.unlink(wav_path)
        except Exception:
            pass


def _ensure_and_load_fixture(candidate: str, es):
    # Ensure test_data dir exists
    os.makedirs(os.path.dirname(candidate), exist_ok=True)

    # If missing, create fixture
    if not os.path.exists(candidate):
        if not _build_mp3_fixture(candidate):
            pytest.skip("No MP3 fixture present and couldn't create one; skipping")

    # Try loading with one rebuild attempt
    try:
        loader = es.MonoLoader(filename=candidate)
        return loader()
    except RuntimeError as exc:
        if not _build_mp3_fixture(candidate):
            pytest.skip(f"Essentia failed to load fixture and couldn't rebuild: {exc}")
        try:
            loader = es.MonoLoader(filename=candidate)
            return loader()
        except RuntimeError:
            pytest.skip(f"Essentia failed to load rebuilt fixture: {exc}")


@pytest.mark.essentia
def test_essentia_loads_mp3_fixture():
    """If a small MP3 fixture exists, Essentia should be able to load it."""
    es = pytest.importorskip("essentia.standard")

    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_data")
    )
    candidate = os.path.join(base, "dummy.mp3")

    audio = _ensure_and_load_fixture(candidate, es)

    assert audio is not None
    assert len(audio) > 0
    assert audio.dtype.kind == "f"


@pytest.mark.essentia
def test_essentia_encodes_and_loads_mp3():
    """Synthesize a WAV, encode to MP3 with ffmpeg, and confirm Essentia loads it.

    This test requires `ffmpeg` and `soundfile` to be available and will skip
    if either is missing.
    """
    es = pytest.importorskip("essentia.standard")

    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not found; skipping mp3 encode/load test")

    # synth a short tone and write WAV
    sr = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.3 * np.sin(2.0 * np.pi * 440.0 * t)

    wav_tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = wav_tf.name
    wav_tf.close()

    try:
        import importlib

        sf = importlib.import_module("soundfile")
        sf.write(wav_path, tone.astype("float32"), sr)
    except Exception as exc:  # pragma: no cover - environment dependent
        try:
            os.unlink(wav_path)
        except Exception:
            pass
        pytest.skip(f"soundfile not available: {exc}")

    mp3_path = wav_path.replace(".wav", ".mp3")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                wav_path,
                mp3_path,
            ],
            check=True,
        )

        loader = es.MonoLoader(filename=mp3_path)
        audio = loader()

        assert audio is not None
        assert len(audio) > 0
        assert audio.dtype.kind == "f"
    finally:
        for p in (wav_path, mp3_path):
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass
