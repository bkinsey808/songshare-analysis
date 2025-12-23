from songshare_analysis.essentia.analysis_to_tags import analysis_to_id3


def test_analysis_to_id3_basic():
    analysis = {
        "provenance": {"tool": "essentia", "version": "2.1"},
        "analysis": {
            "rhythm": {"bpm": 120.0, "beats": [0.5, 1.0], "beat_cv": 0.001},
            "tonal": {"key": "C major", "key_strength": 0.8},
            "tuning": {"reference_hz": 440.0, "cents_offset": 0.0},
        },
    }

    tags = analysis_to_id3(analysis)
    assert tags["TBPM"] == "120.0"
    assert tags["TKEY"] == "C major"
    assert "TXXX:provenance" in tags
    assert tags.get("TXXX:tuning_ref_hz") == "440.0"
