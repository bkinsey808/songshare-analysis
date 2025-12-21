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
    monkeypatch: Any, caplog: pytest.LogCaptureFixture, capsys: Any
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3_identical)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_musicbrainz_lookup_identical)

    # Ensure that apply_metadata is NOT called
    import songshare_analysis.id3_cli_apply as id3_apply

    called = {"applied": False}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--fetch-metadata", "--apply-metadata", "--yes"])

    # No apply should have been called
    assert not called["applied"]

    # Should log that there are no proposed metadata changes
    assert any(
        "No proposed metadata to apply" in r.getMessage() for r in caplog.records
    )

    # And nothing should have been printed to stdout about proposed metadata
    out = capsys.readouterr().out
    assert "Proposed metadata:" not in out


# New test: when core frames exist but identical TXXX proposed frames are present,
# the apply would not make any changes and the preview should be suppressed.


def _fake_read_id3_with_proposed(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {
            "TIT2": "01 The Mystic's Dream",
            "TPE1": "Loreena McKennitt",
            "TALB": "Celtic Myst: Top 100",
            "TXXX:musicbrainz_proposed_TIT2": "The Mystic's Dream",
            "TXXX:musicbrainz_proposed_TPE1": "Loreena McKennitt",
            "TXXX:musicbrainz_proposed_TALB": "Celtic Myst: Top 100",
        },
        "info": {},
    }


def _fake_musicbrainz_lookup_matching_proposed(tags: dict[str, Any]) -> dict[str, str]:
    return {
        "recording_title": "The Mystic's Dream",
        "artist": "Loreena McKennitt",
        "release_title": "Celtic Myst: Top 100",
    }


def test_cli_id3_suppresses_when_only_proposed_frames_already_exist(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture, capsys: Any
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3_with_proposed)
    monkeypatch.setattr(
        id3mb,
        "musicbrainz_lookup",
        _fake_musicbrainz_lookup_matching_proposed,
    )

    import songshare_analysis.id3_cli_apply as id3_apply

    called = {"applied": False}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--fetch-metadata", "--apply-metadata", "--yes"])

    # No apply should have been called because the TXXX proposed frames already exist
    assert not called["applied"]

    # Should log that there are no proposed metadata changes
    assert any(
        "No proposed metadata to apply" in r.getMessage() for r in caplog.records
    )

    # And nothing should have been printed to stdout about proposed metadata
    out = capsys.readouterr().out
    assert "Proposed metadata:" not in out
