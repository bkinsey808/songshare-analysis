# pyright: reportMissingImports=false
from pathlib import Path

import pytest

from songshare_analysis.__main__ import main


def test_cli_id3_prints_tags(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    p = tmp_path / "cli_test.mp3"
    p.write_bytes(b"")

    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2
    except Exception as exc:  # pragma: no cover - test dependency
        pytest.skip("mutagen not available: %s" % exc)

    tags = ID3()  # type: ignore
    tags.add(TIT2(encoding=3, text=["CLI Title"]))  # type: ignore
    tags.save(str(p))

    caplog.set_level(logging.INFO)
    main(["id3", str(p), "--verbose"])

    assert any("File:" in r.getMessage() for r in caplog.records)
    assert any("TIT2" in r.getMessage() for r in caplog.records)
    assert any("CLI Title" in r.getMessage() for r in caplog.records)
