import pytest

from songshare_analysis.__main__ import main


def test_main_csv_flag(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--csv"])
    captured = capsys.readouterr()
    # CSV header should include 'song' and 'plays'
    assert "song,plays" in captured.out
