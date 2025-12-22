# Moved from root tests: rbfetch-missing behavior
from pathlib import Path
from typing import Any

import pytest

from songshare_analysis.__main__ import main


def _fake_read_with_all_tags(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {"TIT2": "A", "TPE1": "B", "TALB": "C"},
        "info": {},
    }


def _fake_read_missing_tags(path: Path) -> dict[str, Any]:
    return {"path": str(path), "tags": {"TIT2": "A"}, "info": {}}


def test_mb_fetch_missing_skips_when_tags_present(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_with_all_tags)

    called = {"mb": False}

    def fake_mb(tags: dict[str, Any]) -> dict[str, Any]:
        called["mb"] = True
        return {}

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--fetch-metadata", "--mb-fetch-missing", "--verbose"])
    assert any("Skipping MusicBrainz lookup" in r.getMessage() for r in caplog.records)
    assert not called["mb"]


def test_mb_fetch_missing_fetches_when_missing(monkeypatch: Any) -> None:
    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_missing_tags)

    called = {"mb": False}

    def fake_mb(tags: dict[str, Any]) -> dict[str, Any]:
        called["mb"] = True
        return {"recording_title": "Found"}

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    main(["id3", "dummy.mp3", "--fetch-metadata", "--mb-fetch-missing"])
    assert called["mb"]
