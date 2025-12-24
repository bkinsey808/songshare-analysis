# pyright: reportMissingImports=false
from pathlib import Path

import pytest

from songshare_analysis.cli.__main__ import main


def test_cli_id3_prints_tags(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    p = tmp_path / "cli_test.mp3"
    p.write_bytes(b"")

    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2
    except Exception as exc:  # pragma: no cover - test dependency
        pytest.skip("mutagen not available: %s" % exc)

    tags = ID3()
    tags.add(TIT2(encoding=3, text=["CLI Title"]))
    tags.save(str(p))

    caplog.set_level(logging.INFO)
    main(["id3", str(p), "--verbose"])

    assert any("File:" in r.getMessage() for r in caplog.records)
    assert any("TIT2" in r.getMessage() for r in caplog.records)
    assert any("CLI Title" in r.getMessage() for r in caplog.records)


def _fake_read_id3(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "tags": {"TIT2": "SongTitle", "TPE1": "ArtistName"},
        "info": {"length": 123},
    }


def test_cli_id3_prints_tags_with_mocked_data(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test CLI prints tags with mocked data."""
    import logging

    import songshare_analysis.cli.id3_cli_process as id3_process

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)
    caplog.set_level(logging.INFO)
    main(["id3", "test_data/dummy.mp3", "--verbose"])

    assert any("File:" in r.getMessage() for r in caplog.records)
    assert any("Tags:" in r.getMessage() for r in caplog.records)
    assert any("TIT2" in r.getMessage() for r in caplog.records)
    assert any("TPE1" in r.getMessage() for r in caplog.records)


def test_print_proposed_metadata_empty_value_no_colon(capsys):
    # Directly test pretty-printer for the empty-value TXXX case
    from songshare_analysis.cli.id3_cli_print import _print_proposed_metadata

    proposed = {
        "TXXX:panns 0 Speech synthesizer": "",
        "TIT2": "Short Title",
    }
    _print_proposed_metadata(proposed)
    out = capsys.readouterr().out

    # Empty-valued TXXX should be printed without a trailing colon/space
    assert "  TXXX:panns 0 Speech synthesizer\n" in out
    assert "  TXXX:panns 0 Speech synthesizer: " not in out
    # Normal tags still show colon + value
    assert "  TIT2: Short Title\n" in out
