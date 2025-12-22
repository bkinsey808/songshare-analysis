from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import pytest

if TYPE_CHECKING:
    # Import the Protocol used for typing ID3-like tag containers. Tests
    # use `cast("ID3Like", ...)` when they need to treat an untyped
    # runtime object as the protocol.
    from songshare_analysis.types import ID3Like

from songshare_analysis import id3_cover as id3mod


def test_embed_cover_skips_when_present(tmp_path: Path) -> None:
    p = tmp_path / "has_cover.mp3"
    p.write_bytes(b"\x00" * 128)

    try:
        from mutagen.id3 import ID3

        mod = __import__("mutagen.id3._frames", fromlist=("APIC",))
        APIC: Any = mod.APIC
    except Exception:
        pytest.skip("mutagen not available")

    # Create initial APIC so embed should be skipped
    ID3_ctor: Callable[..., "ID3Like"] = ID3
    tmp = ID3_ctor()
    tags: ID3Like = tmp
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=b"x"))
    tags.save(str(p))

    called = {"downloaded": False}

    def fake_download(url: str, timeout: int = 10, retries: int = 2) -> bytes:
        called["downloaded"] = True
        return b"jpegdata"

    # Monkeypatch the downloader
    id3mod._download_cover_art = fake_download

    # Should return None (skipped) and should not call downloader
    ok = id3mod._embed_cover_if_needed(p, "https://example.com/cover.jpg")
    assert ok is None
    assert not called["downloaded"]


def test_embed_cover_downloads_and_embeds(tmp_path: Path) -> None:
    p = tmp_path / "no_cover.mp3"
    p.write_bytes(b"\x00" * 128)

    try:
        from mutagen.id3 import ID3
    except Exception:
        pytest.skip("mutagen not available")

    def fake_download(url: str, timeout: int = 10, retries: int = 2) -> bytes:
        # Minimal valid JPEG header (not a full image but OK for APIC presence)
        return b"\xff\xd8\xff\xd9"

    id3mod._download_cover_art = fake_download

    # Should return True and embed
    ok = id3mod._embed_cover_if_needed(p, "https://example.com/cover.jpg")
    assert ok is True

    ID3_ctor: Callable[..., "ID3Like"] = ID3
    tmp = ID3_ctor(str(p))
    tags: ID3Like = tmp
    apics = tags.getall("APIC")
    assert apics


def test_embed_cover_handles_download_errors(tmp_path: Path) -> None:
    p = tmp_path / "no_cover_failure.mp3"
    p.write_bytes(b"\x00" * 128)

    def fake_download(
        url: str,
        timeout: int = 10,
        retries: int = 2,
    ) -> bytes:  # pragma: no cover - simulated
        raise RuntimeError("network down")

    id3mod._download_cover_art = fake_download

    ok = id3mod._embed_cover_if_needed(p, "https://example.com/cover.jpg")
    assert ok is False


def test_cli_id3_shows_cover_embed_proposal_and_embeds(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI integration for cover art embedding through the id3 command."""
    import logging
    from typing import Any

    import songshare_analysis.cli.id3_cli_apply as id3_apply
    import songshare_analysis.cli.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb
    from songshare_analysis.cli.__main__ import main

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

    called = {"embed": False, "applied": False}

    def fake_download(url: str, timeout: int = 5, retries: int = 2) -> bytes:
        return b"img"

    def fake_embed_mp3(
        path: Path,
        image_bytes: bytes,
        mime: str = "image/jpeg",
    ) -> None:
        called["embed"] = True

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    monkeypatch.setattr(id3mod, "_download_cover_art", fake_download)
    monkeypatch.setattr(id3mod, "_embed_cover_mp3", fake_embed_mp3)
    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)
    main(
        [
            "id3",
            "test_data/dummy.mp3",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
        ],
    )

    out = capsys.readouterr().out
    assert "Will embed cover art" in out
    assert called["embed"] is True
    assert called["applied"] is False
