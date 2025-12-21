from pathlib import Path
from typing import Any

import pytest

from songshare_analysis.__main__ import main


def test_cli_id3_shows_cover_embed_proposal_and_embeds(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture, capsys: Any
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    # Existing core frames already match MB values, and there is no embedded art
    def _fake_read_id3_no_cover(path: Path) -> dict[str, Any]:
        return {
            "path": str(path),
            "tags": {
                "TIT2": "The Mystic's Dream",
                "TPE1": "Loreena McKennitt",
                "TALB": "Celtic Myst: Top 100",
            },
            "info": {},
        }

    def _fake_mb_with_cover(tags: dict[str, Any]) -> dict[str, Any]:
        return {
            "recording_title": "The Mystic's Dream",
            "artist": "Loreena McKennitt",
            "release_title": "Celtic Myst: Top 100",
            "cover_art": "https://example.com/cover.jpg",
        }

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3_no_cover)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_mb_with_cover)

    import songshare_analysis.id3_cli_apply as id3_apply
    import songshare_analysis.id3_cover as id3_cover

    called = {"embed": False, "applied": False}

    # Simulate successful download and embedding via bytes
    def fake_download(url: str, timeout: int = 5, retries: int = 2) -> bytes:
        return b"img"

    def fake_embed_mp3(
        path: Path, image_bytes: bytes, mime: str = "image/jpeg"
    ) -> None:
        called["embed"] = True

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    monkeypatch.setattr(id3_cover, "_download_cover_art", fake_download)
    monkeypatch.setattr(id3_cover, "_embed_cover_mp3", fake_embed_mp3)
    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)
    main(
        [
            "id3",
            "dummy.mp3",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
        ]
    )

    out = capsys.readouterr().out
    assert "Will embed cover art" in out

    # Embed should have been attempted, apply should NOT be called (no metadata delta)
    assert called["embed"] is True
    assert called["applied"] is False


def test_cli_suppresses_cover_proposal_if_download_fails(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture, capsys: Any
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_cover as id3_cover
    import songshare_analysis.id3_mb as id3mb

    def _fake_read_id3_no_cover(path: Path) -> dict[str, Any]:
        return {
            "path": str(path),
            "tags": {"TIT2": "T", "TPE1": "A", "TALB": "L"},
            "info": {},
        }

    def _fake_mb_with_cover(tags: dict[str, Any]) -> dict[str, Any]:
        return {
            "recording_title": "T",
            "artist": "A",
            "release_title": "L",
            "cover_art": "u",
        }

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3_no_cover)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_mb_with_cover)

    # Simulate download failure
    def fake_download(url: str, timeout: int = 5, retries: int = 2) -> bytes:
        raise RuntimeError("failed")

    monkeypatch.setattr(id3_cover, "_download_cover_art", fake_download)

    called = {"embed": False}

    def fake_embed(path: Path, url: str) -> bool:
        called["embed"] = True
        return True

    monkeypatch.setattr(id3_cover, "_embed_cover_if_needed", fake_embed)

    caplog.set_level(logging.INFO)
    main(
        [
            "id3",
            "dummy.mp3",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
        ]
    )

    out = capsys.readouterr().out
    assert "Will embed cover art" not in out
    assert called["embed"] is False


def test_cli_id3_suppresses_cover_proposal_when_art_exists(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture, capsys: Any
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    def _fake_read_has_cover(path: Path) -> dict[str, Any]:
        return {
            "path": str(path),
            "tags": {"TIT2": "T", "TPE1": "A", "TALB": "L", "APIC:": b"\xff\xff"},
            "info": {},
        }

    def _fake_mb_with_cover(tags: dict[str, Any]) -> dict[str, Any]:
        return {
            "recording_title": "T",
            "artist": "A",
            "release_title": "L",
            "cover_art": "u",
        }

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_has_cover)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_mb_with_cover)

    import songshare_analysis.id3_cli_apply as id3_apply
    import songshare_analysis.id3_cover as id3_cover

    called = {"embed": False, "applied": False}

    def fake_embed(path: Path, url: str) -> bool:
        called["embed"] = True
        return True

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    monkeypatch.setattr(id3_cover, "_embed_cover_if_needed", fake_embed)
    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)
    main(
        [
            "id3",
            "dummy.mp3",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
        ]
    )

    out = capsys.readouterr().out
    assert "Will embed cover art" not in out

    # Should not attempt embed (already present) and should not apply
    assert called["embed"] is False
    assert called["applied"] is False
