import pytest

from songshare_analysis.__main__ import main


def test_cli_summary_flag(caplog: pytest.LogCaptureFixture) -> None:
    # Call main with `--summary` and capture the logging output via caplog
    import logging

    caplog.set_level(logging.INFO)
    main(["--summary"])
    assert any("Summary:" in rec.getMessage() for rec in caplog.records)


def test_cli_csv_flag(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--csv"])
    captured = capsys.readouterr()
    # CSV header should include 'song' and 'plays'
    assert "song,plays" in captured.out


def test_cli_default_print(capsys: pytest.CaptureFixture[str]) -> None:
    # Default behavior should print a table-style DataFrame
    main([])
    captured = capsys.readouterr()
    assert "song" in captured.out and "plays" in captured.out
