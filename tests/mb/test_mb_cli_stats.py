from __future__ import annotations

from pathlib import Path

import pytest

from songshare_analysis.__main__ import main


def test_cli_stats_counts_apply_and_embed(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb
    from songshare_analysis import id3_cover

    def fake_iter(path: Path, recursive: bool) -> list[Path]:
        return [Path("a.mp3"), Path("b.mp3"), Path("c.mp3")]

    def fake_read(p: Path) -> dict[str, object]:
        return {"path": str(p), "tags": {"TIT2": "X"}, "info": {}}

    monkeypatch.setattr(id3_process, "_iter_audio_files", fake_iter)

    monkeypatch.setattr(id3_process, "read_id3", fake_read)

    monkeypatch.setattr(
        id3mb,
        "musicbrainz_lookup",
        lambda tags: {"cover_art": "https://example.com/cover.jpg"},
    )

    monkeypatch.setattr(id3mb, "propose_metadata_from_mb", lambda mb: {"TIT2": "New"})
    import songshare_analysis.id3_cli_apply as id3_apply

    monkeypatch.setattr(
        id3_apply,
        "propose_metadata_from_mb",
        lambda mb: {"TIT2": "New"},
    )

    def fake_embed(path: Path, url: str) -> bool | None:
        if str(path).endswith("a.mp3"):
            return True
        if str(path).endswith("b.mp3"):
            return False
        return None

    monkeypatch.setattr(id3_cover, "_embed_cover_if_needed", fake_embed)

    applied = {}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        applied[str(path)] = proposed

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)

    main(
        [
            "id3",
            "dummy",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
        ],
    )

    assert "a.mp3" in applied
    assert "c.mp3" in applied
    assert "b.mp3" not in applied

    msgs = [r.getMessage() for r in caplog.records]
    assert sum(1 for m in msgs if m == "Metadata applied (backup created).") == 2

    embedded_count = sum(1 for p in applied if fake_embed(Path(p), ""))
    assert embedded_count == 1

    assert any(
        "Cover art embedding failed; skipping metadata apply for this file." in m
        for m in msgs
    )
