import sys
from pathlib import Path
from typing import Any

import pytest

from songshare_analysis.__main__ import main


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_summary_includes_skipped_count(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process

    def _fake_read_with_mb_ids(path: Path) -> dict[str, Any]:
        return {
            "path": str(path),
            "tags": {
                "TIT2": "A",
                "TPE1": "B",
                "TALB": "C",
                "TXXX:musicbrainz_recording_id": "rec-1",
            },
            "info": {},
        }

    monkeypatch.setattr(
        id3_process, "_iter_audio_files", lambda p, r: [Path("dummy.mp3")]
    )
    monkeypatch.setattr(id3_process, "read_id3", _fake_read_with_mb_ids)

    caplog.set_level(logging.INFO)
    # Capture stdout and verify the summary is printed even without --verbose
    main(
        ["id3", "dummy.mp3", "--fetch-metadata"]
    )  # no --mb-fetch-missing; MB IDs present -> skip
    out = capsys.readouterr().out

    assert "files skipped=1" in out
