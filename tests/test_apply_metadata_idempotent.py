import sys
from pathlib import Path

import pytest

from songshare_analysis import mb as id3mb
from songshare_analysis.types import MBInfo


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_apply_then_no_proposals_on_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Create an MP3 with an existing title
    p = tmp_path / "idempotent.mp3"
    p.write_bytes(b"\x00" * 128)

    pytest.importorskip("mutagen.id3")

    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2

        tags = ID3()  # type: ignore
        tags.add(TIT2(encoding=3, text=["Om Test"]))  # type: ignore
        tags.save(str(p))
    except Exception:
        pytest.skip("mutagen not available or couldn't write test tags")

    # Fake MB lookup that proposes different metadata
    def fake_mb(*_: object) -> MBInfo:
        return {
            "recording_id": "rec-42",
            "recording_title": "Test Song",
            "artist": "Test Artist",
            "release_title": "Test Release",
            "release_id": "rel-99",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    # First run: should print proposals
    from songshare_analysis.__main__ import main

    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])
    out1 = capsys.readouterr().out
    assert "Proposed metadata:" in out1
    assert "Applied metadata to" in out1

    # Second run: should not print proposals (already applied)
    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])
    out2 = capsys.readouterr().out
    assert "Proposed metadata:" not in out2
    assert "Applied metadata to" not in out2
