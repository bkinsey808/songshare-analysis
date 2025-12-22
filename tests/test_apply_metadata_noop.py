import sys
from pathlib import Path

import pytest

from songshare_analysis.types import MBInfo


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_detect_noop_apply_logs_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """If apply_metadata is a no-op (doesn't change the file) we should
    detect it after a successful apply call and warn that the write may have
    failed, and not count the file as applied.
    """
    # Create an MP3 with an existing title
    p = tmp_path / "noop_apply.mp3"
    p.write_bytes(b"\x00" * 128)

    pytest.importorskip("mutagen.id3")

    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2

        tags = ID3()  # type: ignore
        tags.add(TIT2(encoding=3, text=["Existing Title"]))  # type: ignore
        tags.save(str(p))
    except Exception:
        pytest.skip("mutagen not available or couldn't write test tags")

    # Fake MB lookup that proposes different metadata
    def fake_mb(*_: object) -> MBInfo:
        return {
            "recording_id": "rec-noop",
            "recording_title": "New Title",
            "artist": "New Artist",
            "release_title": "New Release",
            "release_id": "rel-noop",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr("songshare_analysis.mb.musicbrainz_lookup", fake_mb)

    # Monkeypatch apply_metadata to be a no-op so it reports success but doesn't
    # actually change the file.
    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        # intentionally do nothing
        return None

    monkeypatch.setattr("songshare_analysis.id3_cli_apply.apply_metadata", fake_apply)

    caplog.set_level("INFO")
    # Run CLI to fetch + apply with auto-yes
    from songshare_analysis.__main__ import main

    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])

    # We should have logged a warning about the write not taking effect
    assert any(
        "write may have failed" in r.getMessage()
        or "remain unchanged" in r.getMessage()
        or "tags unchanged" in r.getMessage()
        for r in caplog.records
    )

    # Summary should indicate zero applied
    assert any("tags applied=0" in r.getMessage() for r in caplog.records)
