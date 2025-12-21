import pytest

from songshare_analysis.__main__ import main


def test_main_summary_flag(caplog: pytest.LogCaptureFixture) -> None:
    # Call main with `--summary` and capture the logging output via caplog
    import logging

    caplog.set_level(logging.INFO)
    main(["--summary"])
    assert any("Summary:" in rec.getMessage() for rec in caplog.records)
