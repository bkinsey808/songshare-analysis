import sys
from pathlib import Path

import pytest

from songshare_analysis.id3_io import read_id3


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="ID3 tests are POSIX-friendly but should work everywhere",
)
def test_read_id3_on_created_mp3(tmp_path: Path) -> None:
    p = tmp_path / "test.mp3"
    p.write_bytes(b"")

    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2, TPE1
    except Exception as exc:  # pragma: no cover - test dependency
        pytest.skip("mutagen not available: %s" % exc)

    tags = ID3()  # type: ignore
    tags.add(TIT2(encoding=3, text=["Test Title"]))  # type: ignore
    tags.add(TPE1(encoding=3, text=["Some Artist"]))  # type: ignore
    tags.save(str(p))

    info = read_id3(p)
    assert info["path"] == str(p)
    assert "TIT2" in info["tags"]
    assert "Test Title" in info["tags"]["TIT2"]
    assert "TPE1" in info["tags"]
