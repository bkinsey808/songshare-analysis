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


def test_analysis_to_id3_genre_applied_when_confident():
    analysis = {
        "provenance": {"tool": "panns", "version": "0.1"},
        "analysis": {},
        "semantic": {"genre": {"top": "Folk", "top_confidence": 0.9}},
    }
    tags = analysis_to_id3(analysis)
    assert tags.get("TCON") == "Folk"
    assert "TXXX:genre_top_confidence" in tags


def test_genre_music_is_filtered():
    analysis = {
        "provenance": {"tool": "panns", "version": "0.1"},
        "analysis": {},
        "semantic": {"genre": {"top": "Music", "top_confidence": 0.8}},
    }

    tags = analysis_to_id3(analysis)
    assert "TCON" not in tags
    assert tags.get("TXXX:genre_top") == "Music"


def test_genre_specific_is_applied():
    analysis = {
        "provenance": {"tool": "panns", "version": "0.1"},
        "analysis": {},
        "semantic": {"genre": {"top": "Jazz", "top_confidence": 0.9}},
    }

    tags = analysis_to_id3(analysis)
    assert tags.get("TCON") == "Jazz"
    assert "TXXX:genre_top" not in tags


def test_analysis_to_id3_genre_not_applied_when_low_confidence():
    analysis = {
        "provenance": {"tool": "panns", "version": "0.1"},
        "analysis": {},
        "semantic": {"genre": {"top": "Folk", "top_confidence": 0.1}},
    }
    tags = analysis_to_id3(analysis)
    assert tags.get("TCON") is None


def test_panns_panns_decile_tags_generated():
    # Create a controlled probs_dict with 10 labels (0.1 .. 1.0) so each
    # falls into its own decile 0..9 and we can assert tag names/values.
    probs = {f"g{i}": (i + 1) / 10.0 for i in range(10)}
    analysis = {
        "provenance": {"tool": "panns", "version": "0.1"},
        "analysis": {},
        "semantic": {"genre": {"top": "g10", "top_confidence": 0.95, "probs_dict": probs}},
    }
    tags = analysis_to_id3(analysis)

    # Expect a TXXX tag per label with the decile in the desc
    for i in range(10):
        label = f"g{i}"
        decile = i  # deterministic for this synthetic distribution
        key = f"TXXX:panns {decile} {label}"
        assert key in tags
        assert float(tags[key]) == probs[label]
