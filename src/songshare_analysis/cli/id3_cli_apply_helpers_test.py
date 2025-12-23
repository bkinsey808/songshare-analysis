from __future__ import annotations

import builtins
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

import songshare_analysis.cli.id3_cli_apply as id3_apply
import songshare_analysis.cli.id3_cli_print as id3_print
import songshare_analysis.id3_cover as id3mod


def test_print_proposed_metadata_truncation(capsys: pytest.CaptureFixture[str]) -> None:
    long_val = "x" * 500
    proposed = {"long": long_val, "cover": b"\x00" * 10}

    id3_print._print_proposed_metadata(proposed)
    out = capsys.readouterr().out

    assert "Proposed metadata:" in out
    assert "<binary data 10 bytes>" in out
    # long value should be truncated with ellipsis
    assert "..." in out


def test_confirm_apply_yes_flag() -> None:
    args = SimpleNamespace(yes=True)
    assert id3_apply._confirm_apply(args) is True


def test_confirm_apply_user_input(monkeypatch: pytest.MonkeyPatch) -> None:
    args = SimpleNamespace(yes=False)

    monkeypatch.setattr(builtins, "input", lambda prompt="": "y")
    assert id3_apply._confirm_apply(args) is True

    monkeypatch.setattr(builtins, "input", lambda prompt="": "n")
    assert id3_apply._confirm_apply(args) is False


def test_maybe_embed_cover_skips_when_not_requested() -> None:
    args = SimpleNamespace(embed_cover_art=False)
    assert (
        id3_apply._maybe_embed_cover(
            Path("foo.mp3"),
            args,
            {},
            logging.getLogger("test"),
        )
        is None
    )

    args = SimpleNamespace(embed_cover_art=True)
    # missing cover_art key -> skipped
    assert (
        id3_apply._maybe_embed_cover(
            Path("foo.mp3"),
            args,
            {},
            logging.getLogger("test"),
        )
        is None
    )


def test_maybe_embed_cover_calls_embed_and_handles_results(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    args = SimpleNamespace(embed_cover_art=True)
    mb_info = {"cover_art": "https://example.com/cover.jpg"}

    logger = logging.getLogger("test")

    # Return True -> propagated, no warning
    monkeypatch.setattr(id3mod, "_embed_cover_if_needed", lambda p, u: True)
    res = id3_apply._maybe_embed_cover(Path("foo.mp3"), args, mb_info, logger)
    assert res is True
    assert not any(
        "Cover art embedding failed" in r.getMessage() for r in caplog.records
    )

    # Return False -> returns False (logging suppressed)
    monkeypatch.setattr(id3mod, "_embed_cover_if_needed", lambda p, u: False)
    res = id3_apply._maybe_embed_cover(Path("foo.mp3"), args, mb_info, logger)
    assert res is False


def test_apply_metadata_safe_logs_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    # Cause apply_metadata to raise
    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        raise RuntimeError("boom")

    import songshare_analysis.cli.id3_cli_apply as id3_apply

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    class DummyLogger:
        def __init__(self) -> None:
            self.called = False
            self.msg = ""

        def error(self, fmt: str, *args: object) -> None:
            self.called = True
            self.msg = fmt % args

    logger = DummyLogger()
    id3_apply._apply_metadata_safe(Path("f"), {"a": "b"}, logger)

    assert logger.called is True
    assert "Failed to apply metadata" in logger.msg
