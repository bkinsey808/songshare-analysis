from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from songshare_analysis.genre import panns


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
    # Ensure panns_inference is not importable
    if "panns_inference" in sys.modules:
        del sys.modules["panns_inference"]

    audio = tmp_path / "f.wav"
    audio.write_text("fake")

    with pytest.raises(panns.PannsNotInstalled):
        panns.infer_genre_panns(audio)
