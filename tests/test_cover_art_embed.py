from pathlib import Path
from typing import TYPE_CHECKING, Callable

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
        APIC = mod.APIC
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
