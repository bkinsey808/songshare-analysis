from pathlib import Path
from typing import Any

import pytest

from songshare_analysis.__main__ import main


def _fake_read_id3_identical(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {"TIT2": "SongTitle", "TPE1": "ArtistName"},
        "info": {"length": 123},
    }


def _fake_musicbrainz_lookup_identical(tags: dict[str, Any]) -> dict[str, str]:
    # Returns values that are identical to the current tags
    return {"recording_title": "SongTitle", "artist": "ArtistName"}


def test_cli_id3_apply_skips_when_proposed_matches_existing(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
    capsys: Any,
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3_identical)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_musicbrainz_lookup_identical)

    import songshare_analysis.id3_cli_apply as id3_apply

    called = {"applied": False}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--fetch-metadata", "--apply-metadata", "--yes"])

    assert not called["applied"]
    assert any(
        "No proposed metadata to apply" in r.getMessage() for r in caplog.records
    )
    out = capsys.readouterr().out
    assert "Proposed metadata:" not in out
