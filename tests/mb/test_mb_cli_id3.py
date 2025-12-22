# Moved from root tests; MusicBrainz-related CLI tests for id3
from pathlib import Path
from typing import Any

import pytest

from songshare_analysis.__main__ import main


def _fake_read_id3(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {"TIT2": "SongTitle", "TPE1": "ArtistName"},
        "info": {"length": 123},
    }


def _fake_musicbrainz_lookup(tags: dict[str, Any]) -> dict[str, str]:
    return {"recording_title": "Found"}


def _fake_propose_metadata_from_mb(mb: dict[str, Any]) -> dict[str, str]:
    return {"TIT2": "NewTitle"}


def test_cli_id3_prints_tags(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)
    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--verbose"])

    assert any("File:" in r.getMessage() for r in caplog.records)
    assert any("Tags:" in r.getMessage() for r in caplog.records)
    assert any("TIT2" in r.getMessage() for r in caplog.records)
    assert any("TPE1" in r.getMessage() for r in caplog.records)


def test_cli_id3_fetch_metadata(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_musicbrainz_lookup)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--fetch-metadata", "--verbose"])

    assert any("MusicBrainz" in r.getMessage() for r in caplog.records)
    assert any(
        "recording_title" in r.getMessage() or "Found" in r.getMessage()
        for r in caplog.records
    )
