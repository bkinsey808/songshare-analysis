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
        "semantic": {
            "genre": {"top": "g10", "top_confidence": 0.95, "probs_dict": probs}
        },
    }
    tags = analysis_to_id3(analysis)

    # Expect we have a TXXX:panns <label> key per label with the decile
    # as its value (highest-prob label first - g9 here).
    panns_keys = [k for k in tags.keys() if k.startswith("TXXX:panns ")]
    assert panns_keys, "No panns tags found"
    # First key should correspond to the highest-prob label g9
    first_label = panns_keys[0].split(" ", 2)[2]
    assert first_label == "g9"
    # Each label should have a key with its decile value
    for i in range(10):
        key = f"TXXX:panns g{i}"
        assert key in tags
        assert tags[key] == str(i)


def test_panns_panns_tags_sorted_by_prob():
    probs = {"a": 0.1, "b": 0.9, "c": 0.5}
    analysis = {
        "provenance": {"tool": "panns", "version": "0.1"},
        "analysis": {},
        "semantic": {
            "genre": {"top": "b", "top_confidence": 0.95, "probs_dict": probs}
        },
    }
    tags = analysis_to_id3(analysis)

    # Extract panns tag keys in insertion order and ensure highest-prob label first
    panns_keys = [k for k in tags.keys() if k.startswith("TXXX:panns ")]
    assert panns_keys, "No panns tags found"
    # First panns key should be for 'b' (0.9)
    first_label = panns_keys[0].split(" ", 2)[2]
    assert first_label == "b"
    # Verify values are the deciles computed from the sidecar helper
    from songshare_analysis.essentia.analysis_to_tags import compute_panns_deciles

    genre = {"probs_dict": probs}
    rows = compute_panns_deciles(genre)
    decile_map = {r["label"]: str(r["decile"]) for r in rows}
    for k in panns_keys:
        label = k.split(" ", 2)[2]
        assert tags[k] == decile_map[label]


def test_compute_panns_deciles():
    # Controlled 10-label distribution where probs 0.1..1.0 map to deciles 0..9
    probs = {f"g{i}": (i + 1) / 10.0 for i in range(10)}
    genre = {"probs_dict": probs}

    from songshare_analysis.essentia.analysis_to_tags import compute_panns_deciles

    rows = compute_panns_deciles(genre)
    assert isinstance(rows, list)
    # Should have one row per label and be sorted descending by prob
    assert len(rows) == 10
    probs_in_rows = [r["prob"] for r in rows]
    assert probs_in_rows == sorted(probs_in_rows, reverse=True)
    # Verify deciles present and deterministic
    for r in rows:
        assert 0 <= r["decile"] <= 9
