import sys
from pathlib import Path

import pytest

from songshare_analysis import id3_io as id3io
from songshare_analysis import mb as id3mb
from songshare_analysis.__main__ import main
from songshare_analysis.types import MBInfo


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_apply_metadata_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Create an empty mp3 file
    p = tmp_path / "apply_test.mp3"
    p.write_bytes(b"")

    # Pre-seed the file with a title so lookup will run
    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2

        tags = ID3()  # type: ignore
        tags.add(TIT2(encoding=3, text=["Om Test"]))  # type: ignore
        tags.save(str(p))
    except Exception:
        pytest.skip("mutagen not available or couldn't write test tags")

    # Monkeypatch musicbrainz_lookup to avoid network
    def fake_mb(_tags: dict[str, str]) -> MBInfo:
        return {
            "recording_id": "rec-42",
            "recording_title": "Test Song",
            "artist": "Test Artist",
            "release_title": "Test Release",
            "release_id": "rel-99",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    # Run CLI to fetch + apply with auto-yes
    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])

    # CLI should print a short confirmation to stdout
    out = capsys.readouterr().out
    assert f"File: {p}" in out
    assert "Applied metadata to" in out

    # Read tags and assert written. Since the file had an existing title, it
    # should be preserved and the proposed value recorded in a TXXX frame.
    info = id3io.read_id3(p)
    assert info["tags"].get("TIT2")
    assert "Om Test" in info["tags"].get("TIT2", "")
    assert "Test Song" in info["tags"].get("TXXX:musicbrainz_proposed_TIT2", "")

    # Backup sidecar should exist
    bak = p.with_suffix(p.suffix + ".tags.bak.json")
    assert bak.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_apply_metadata_cli_writes_when_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create an empty mp3 file without a title
    p = tmp_path / "apply_test_no_title.mp3"
    # Ensure file has some space so Mutagen can write ID3 headers reliably
    p.write_bytes(b"\x00" * 128)

    pytest.importorskip("mutagen.id3")

    # Monkeypatch musicbrainz_lookup to avoid network
    def fake_mb(_tags: dict[str, str]) -> MBInfo:
        return {
            "recording_id": "rec-99",
            "recording_title": "Fresh Song",
            "artist": "Fresh Artist",
            "release_title": "Fresh Release",
            "release_id": "rel-99",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    # Instead of invoking the CLI (which relies on existing tags to trigger
    # a lookup), call apply directly with a proposed mapping to verify that
    # applying to a file with no existing title writes the common TIT2 frame.
    proposed = id3mb.propose_metadata_from_mb(fake_mb({}))
    id3io.apply_metadata(p, proposed)

    info = id3io.read_id3(p)
    assert "Fresh Song" in info["tags"].get("TIT2", "")

    # Backup sidecar should exist
    bak = p.with_suffix(p.suffix + ".tags.bak.json")
    assert bak.exists()
