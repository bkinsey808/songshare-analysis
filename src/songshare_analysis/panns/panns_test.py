from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from songshare_analysis.panns import panns


class _FakeTaggerBasic:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.__version__ = "0.0-fake"

    def inference(self, path: str):
        return {"labels": ["Rock", "Jazz"], "probs": [0.83, 0.17]}


class _FakeTaggerClipwise:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.labels = ["Classical", "Electronic"]
        self.__version__ = "0.0-fake"

    def inference(self, path: str):
        import numpy as np

        return {"clipwise_output": np.array([0.2, 0.8])}


def _inject_fake_module(fake_cls, name: str = "SoundTagging"):
    mod = types.ModuleType("panns_inference")
    mod.__dict__[name] = fake_cls
    sys.modules["panns_inference"] = mod


class _FakeTaggerWithCheckpoint(_FakeTaggerBasic):
    def __init__(self, device: str = "cpu"):
        super().__init__(device=device)
        # Simulate the attribute name used by panns to advertise the checkpoint
        self.checkpoint_path = "/home/bkinsey/panns_data/Cnn14_mAP=0.431.pth"


def test_infer_genre_panns_prints_checkpoint(monkeypatch, tmp_path: Path, capsys):
    audio = tmp_path / "f.wav"
    audio.write_text("fake")

    _inject_fake_module(_FakeTaggerWithCheckpoint)

    # Ensure the one-time print happens during this test
    monkeypatch.setattr(panns, "_panns_initialized", False)

    panns.infer_genre_panns(audio)

    captured = capsys.readouterr()
    assert "Using CPU." in captured.out
    assert "Checkpoint path:" in captured.out
    assert "Cnn14_mAP=0.431.pth" in captured.out


def test_infer_genre_panns_basic(monkeypatch, tmp_path: Path):
    audio = tmp_path / "f.wav"
    audio.write_text("fake")

    _inject_fake_module(_FakeTaggerBasic)

    out = panns.infer_genre_panns(audio)

    assert out["provenance"]["model"] == "panns-inference"
    assert out["top"] == "Rock"
    assert out["top_confidence"] == pytest.approx(0.83)
    assert "probs_dict" in out and isinstance(out["probs_dict"], dict)


def test_infer_genre_panns_with_audio_tagging(monkeypatch, tmp_path: Path):
    """Support packages that expose `AudioTagging` instead of `SoundTagging`."""
    audio = tmp_path / "f2.wav"
    audio.write_text("fake")

    _inject_fake_module(_FakeTaggerBasic, name="AudioTagging")

    out = panns.infer_genre_panns(audio)

    assert out["top"] == "Rock"

    assert out["provenance"]["model"] == "panns-inference"
    assert out["top"] == "Rock"
    assert out["top_confidence"] == pytest.approx(0.83)
    assert "probs_dict" in out and isinstance(out["probs_dict"], dict)


def test_infer_genre_panns_clipwise(monkeypatch, tmp_path: Path):
    audio = tmp_path / "f.wav"
    audio.write_text("fake")

    _inject_fake_module(_FakeTaggerClipwise)

    out = panns.infer_genre_panns(audio)

    assert out["top"] == "Electronic"
    assert out["top_confidence"] == pytest.approx(0.8)


def test_infer_genre_panns_missing_dependency(tmp_path: Path):
    # If panns_inference is available in the environment, skip this test
    try:
        import importlib.util as _importlib_util

        if _importlib_util.find_spec("panns_inference") is not None:
            pytest.skip(
                "panns_inference installed in environment; "
                "skipping missing-dependency test"
            )
    except Exception:
        pass

    # Simulate panns_inference being missing by forcing import to fail
    import builtins

    orig_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "panns_inference" or name.startswith("panns_inference."):
            raise ImportError
        return orig_import(name, globals, locals, fromlist, level)

    builtins.__import__ = _fake_import

    try:
        audio = tmp_path / "f.wav"
        audio.write_text("fake")

        with pytest.raises(panns.PannsNotInstalled):
            panns.infer_genre_panns(audio)
    finally:
        builtins.__import__ = orig_import
