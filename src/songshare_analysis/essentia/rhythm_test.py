import json
import os

import numpy as np
import pytest

from songshare_analysis.essentia import rhythm


def test_detect_rhythm_clicktrack():
    # perfect metronome at 120 BPM -> 0.5s interval
    beats = [i * 0.5 for i in range(16)]
    analysis = rhythm.detect_rhythm_timing_from_beats(beats)
    assert analysis["n_beats"] == 16
    assert analysis["label"] == "clicktrack"
    assert analysis["beat_cv"] < 0.001
    assert analysis["quant_score"] == 1.0
    assert analysis["confidence"] > 0.9


def test_detect_rhythm_human():
    # human-like jitter: 0.02s std dev
    rng = np.random.default_rng(0)
    beats = [i * 0.5 + float(rng.normal(0.0, 0.02)) for i in range(16)]
    analysis = rhythm.detect_rhythm_timing_from_beats(beats)
    assert analysis["n_beats"] == 16
    assert analysis["label"] in ("human", "uncertain")
    assert analysis["beat_cv"] > 0.002


def test_write_rhythm_id3_tags(tmp_path):
    f = tmp_path / "test.mp3"
    # create empty file; mutagen will add ID3 data
    f.write_bytes(b"\x00\x00")

    analysis = {
        "label": "human",
        "confidence": 0.75,
        "reason": "synthetic",
        "beat_cv": 0.01,
        "quant_score": 0.2,
    }

    rhythm.write_rhythm_id3_tags(str(f), analysis)

    # re-open ID3 and check frames
    from mutagen.id3 import ID3  # type: ignore

    id3 = ID3(str(f))
    # TXXX frames are stored with desc
    human_frames = [
        frame for frame in id3.getall("TXXX") if frame.desc == "rhythm_human"
    ]
    assert human_frames, "TXXX:rhythm_human not found"
    assert (
        human_frames[0].text[0].startswith("0.75") or human_frames[0].text[0] == "0.75"
    )

    label_frames = [
        frame for frame in id3.getall("TXXX") if frame.desc == "rhythm_timing"
    ]
    assert label_frames and label_frames[0].text[0] == "human"

    conf_frames = [
        frame
        for frame in id3.getall("TXXX")
        if frame.desc == "rhythm_timing_confidence"
    ]
    assert conf_frames and float(conf_frames[0].text[0]) == pytest.approx(0.75)

    # sidecar write
    sidecar = rhythm.write_analysis_sidecar(str(f), analysis)
    assert os.path.exists(sidecar)
    with open(sidecar, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["label"] == "human"


def test_analysis_to_id3_includes_rhythm_tags():
    from songshare_analysis.essentia.analysis_to_tags import analysis_to_id3

    beats = [i * 0.5 for i in range(16)]
    timing = rhythm.detect_rhythm_timing_from_beats(beats)
    analysis = {
        "provenance": {"tool": "test", "version": "0.1"},
        "analysis": {"rhythm": {"bpm": 120.0, "beats": beats, "timing": timing}},
    }

    out = analysis_to_id3(analysis)
    assert "TXXX:rhythm_timing" in out
    assert out["TXXX:rhythm_timing"] == "clicktrack"
    assert "TXXX:rhythm_machine" in out
    assert float(out["TXXX:rhythm_machine"]) == pytest.approx(timing["confidence"])
