import pytest
from songshare_analysis.__main__ import main


def test_main_default_print(capsys: pytest.CaptureFixture[str]) -> None:
    # Default behavior should print a table-style DataFrame
    main([])
    captured = capsys.readouterr()
    assert "song" in captured.out and "plays" in captured.out
