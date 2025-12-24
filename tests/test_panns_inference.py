from pathlib import Path

import numpy as np

from songshare_analysis.genre.panns import infer_genre_panns


class FakeModelPathFirst:
    __version__ = "0.1"
    labels = ["a", "b", "c"]

    def __init__(self, device=None):
        pass

    def inference(self, audio):
        # Simulate older behavior that accepts a file path
        if isinstance(audio, str):
            return {"labels": ["a", "b", "c"], "probs": [0.1, 0.2, 0.7]}
        raise RuntimeError("Unexpected input")


class FakeModelArrayOnly:
    __version__ = "0.1"
    labels = ["a", "b", "c"]

    def __init__(self, device=None):
        pass

    def inference(self, audio):
        # Simulate newer API that expects a numpy array and returns (clip, embedding)
        if isinstance(audio, np.ndarray):
            return np.array([0.1, 0.2, 0.7]), np.zeros((128,))
        # Mirror the real failure when passed a path
        raise AttributeError("'str' object has no attribute 'dtype'")


def test_infer_genre_uses_path_behavior(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "songshare_analysis.genre.panns._import_panns",
        lambda: FakeModelPathFirst,
    )

    res = infer_genre_panns(Path("test_data/essentia_fixture.mp3"))
    assert res["top"] == "c"
    assert res["provenance"]["model"] == "panns-inference"


def test_infer_genre_falls_back_to_array(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "songshare_analysis.genre.panns._import_panns",
        lambda: FakeModelArrayOnly,
    )

    res = infer_genre_panns(Path("test_data/essentia_fixture.mp3"))
    assert res["top"] == "c"
    assert res["provenance"]["model"] == "panns-inference"
