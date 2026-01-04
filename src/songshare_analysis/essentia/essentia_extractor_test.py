from pathlib import Path


def test_extract_semantic_adds_panns_deciles(monkeypatch, tmp_path: Path):
    # Prepare a fake PANNs result
    probs = {f"g{i}": (i + 1) / 10.0 for i in range(10)}
    fake_res = {
        "labels": list(probs.keys()),
        "probs": list(probs.values()),
        "probs_dict": probs,
        "top": "g9",
        "top_confidence": 0.95,
    }

    # Ensure the panns module exists and monkeypatch its infer_genre_panns
    import songshare_analysis.panns.panns as panns_mod

    monkeypatch.setattr(panns_mod, "infer_genre_panns", lambda p: fake_res)

    # Call extract_semantic and verify panns_deciles present
    from songshare_analysis.essentia.essentia_extractor import extract_semantic

    audio = tmp_path / "f.mp3"
    audio.write_text("")

    res = extract_semantic(audio)
    assert "semantic" in res
    genre = res["semantic"].get("genre")
    assert isinstance(genre, dict)
    assert "panns_deciles" in genre
    rows = genre["panns_deciles"]
    assert isinstance(rows, list)
    assert len(rows) == 10
    # Verify the top label appears first (highest prob)
    assert rows[0]["label"] == "g9"

    # The sidecar should have the probs_dict ordered highest-first
    genre_sd = res["semantic"]["genre"]
    first_key = next(iter(genre_sd["probs_dict"]))
    assert first_key == "g9"
    assert genre_sd["labels"][0] == "g9"
    assert genre_sd["probs"][0] == probs["g9"]


def test_extract_semantic_essentia_fallback(monkeypatch, tmp_path: Path):
    # Create a fake MusicExtractor that returns a genre
    fake_pool = {"genre.top": "folk", "genre.top_confidence": 0.82}

    class FakeME:
        def __call__(self, audio_in):
            return fake_pool

    class FakeES:
        # MonoLoader should return a callable that returns an audio-like array
        def MonoLoader(self, filename=None):
            class L:
                def __call__(self):
                    return [0.0] * 44100

            return L()

        def MusicExtractor(self):
            return FakeME()

    # Monkeypatch the internal _essentia_import to return our fake es
    import songshare_analysis.essentia.essentia_extractor as ex_mod

    monkeypatch.setattr(ex_mod, "_essentia_import", lambda: (None, FakeES()))

    audio = tmp_path / "f.mp3"
    audio.write_text("")

    res = ex_mod.extract_semantic(audio)
    assert "semantic" in res
    genre = res["semantic"].get("genre")
    assert isinstance(genre, dict)
    assert genre.get("top") == "folk"
    assert abs(genre.get("top_confidence", 0) - 0.82) < 1e-6
