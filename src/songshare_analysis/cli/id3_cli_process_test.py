import sys
from pathlib import Path
from typing import Any

import pytest

from songshare_analysis.cli.__main__ import main


def _fake_read_with_all_tags(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {"TIT2": "A", "TPE1": "B", "TALB": "C"},
        "info": {},
    }


def _fake_read_missing_tags(path: Path) -> dict[str, Any]:
    return {"path": str(path), "tags": {"TIT2": "A"}, "info": {}}


def test_mb_fetch_missing_skips_when_tags_present(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    import songshare_analysis.cli.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_with_all_tags)

    called = {"mb": False}

    def fake_mb(tags: dict[str, Any]) -> dict[str, Any]:
        called["mb"] = True
        return {}

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    caplog.set_level(logging.INFO)
    main(
        [
            "id3",
            "test_data/dummy.mp3",
            "--fetch-metadata",
            "--mb-fetch-missing",
            "--verbose",
        ],
    )
    assert any("Skipping MusicBrainz lookup" in r.getMessage() for r in caplog.records)
    assert not called["mb"]


def test_mb_fetch_missing_fetches_when_missing(monkeypatch: Any) -> None:
    import songshare_analysis.cli.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_missing_tags)

    called = {"mb": False}

    def fake_mb(tags: dict[str, Any]) -> dict[str, Any]:
        called["mb"] = True
        return {"recording_title": "Found"}

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    main(["id3", "test_data/dummy.mp3", "--fetch-metadata", "--mb-fetch-missing"])
    assert called["mb"]


def test_skip_lookup_when_mb_ids_present(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """If MusicBrainz ID TXXX frames already exist, we skip lookup even when
    user requested `--fetch-metadata` (no network call should be made).
    """
    import logging

    import songshare_analysis.cli.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

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

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_with_mb_ids)

    called = {"mb": False}

    def fake_mb(tags: dict[str, Any]) -> dict[str, Any]:
        called["mb"] = True
        return {}

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    caplog.set_level(logging.INFO)
    main(["id3", "test_data/dummy.mp3", "--fetch-metadata", "--verbose"])

    # Silent skip: no MusicBrainz lookup should be performed and no skip
    # log message should be emitted for files already containing MB IDs.
    assert not any(
        "Skipping MusicBrainz lookup" in r.getMessage() for r in caplog.records
    )
    assert not called["mb"]


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_summary_includes_skipped_count(
    monkeypatch: Any,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import logging

    import songshare_analysis.cli.id3_cli_process as id3_process

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
        id3_process, "_iter_audio_files", lambda p, r: [Path("test_data/dummy.mp3")]
    )
    monkeypatch.setattr(id3_process, "read_id3", _fake_read_with_mb_ids)

    caplog.set_level(logging.INFO)
    # Capture stdout and verify the summary is printed even without --verbose
    main(
        ["id3", "test_data/dummy.mp3", "--fetch-metadata"]
    )  # no --mb-fetch-missing; MB IDs present -> skip
    out = capsys.readouterr().out

    assert "Files skipped: 1" in out


def _fake_read_id3(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {"TIT2": "SongTitle", "TPE1": "ArtistName"},
        "info": {"length": 123},
    }


def _fake_musicbrainz_lookup(tags: dict[str, Any]) -> dict[str, str]:
    return {"recording_title": "Found"}


def test_cli_id3_fetch_metadata(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test CLI fetches metadata and logs MusicBrainz results."""
    import logging

    import songshare_analysis.cli.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_musicbrainz_lookup)

    caplog.set_level(logging.INFO)
    main(["id3", "test_data/dummy.mp3", "--fetch-metadata", "--verbose"])

    assert any("MusicBrainz" in r.getMessage() for r in caplog.records)
    assert any(
        "recording_title" in r.getMessage() or "Found" in r.getMessage()
        for r in caplog.records
    )


def test_analyze_includes_semantic_genre(monkeypatch: Any, tmp_path: Path) -> None:
    """If --analyze is used and semantic inference is available, the sidecar
    should include a `semantic.genre` block from the model."""

    import songshare_analysis.cli.id3_cli_process as id3_process

    written: list[dict] = []

    def fake_write_sidecar(path: Path, analysis: dict) -> Path:
        written.append(analysis)
        # Return a plausible sidecar path
        return path.with_suffix(path.suffix + ".analysis.json")

    # Replace IO with fakes
    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)

    def fake_extract_basic(p: Path) -> dict:
        return {"analysis": {}}

    monkeypatch.setattr(
        id3_process.essentia_extractor, "extract_basic", fake_extract_basic
    )

    # Provide a fake semantic result via extract_semantic
    def fake_semantic(p: Path) -> dict:
        return {"semantic": {"genre": {"top": "Rock", "top_confidence": 0.83}}}

    monkeypatch.setattr(
        id3_process.essentia_extractor, "extract_semantic", fake_semantic
    )
    monkeypatch.setattr(
        id3_process.essentia_extractor, "write_analysis_sidecar", fake_write_sidecar
    )

    main(["id3", "test_data/dummy.mp3", "--analyze"])  # should call our fakes

    assert written, "Sidecar write should have been called"
    analysis = written[0]
    assert "semantic" in analysis and "genre" in analysis["semantic"]
    assert analysis["semantic"]["genre"]["top"] == "Rock"


def test_verbose_prints_proposed_tags_on_analyze(
    monkeypatch: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """When `--analyze --verbose` is used, the CLI should print proposed tags."""
    import songshare_analysis.cli.id3_cli_process as id3_process

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)

    def fake_extract_basic(p: Path) -> dict:
        return {"analysis": {}}

    monkeypatch.setattr(
        id3_process.essentia_extractor, "extract_basic", fake_extract_basic
    )

    def fake_semantic(p: Path) -> dict:
        return {"semantic": {"genre": {"top": "Funk", "top_confidence": 0.95}}}

    monkeypatch.setattr(
        id3_process.essentia_extractor, "extract_semantic", fake_semantic
    )

    def fake_write_sidecar(path: Path, analysis: dict) -> Path:
        # write a fake sidecar path and capture the analysis for inspection
        return path.with_suffix(path.suffix + ".analysis.json")

    monkeypatch.setattr(
        id3_process.essentia_extractor, "write_analysis_sidecar", fake_write_sidecar
    )

    # Run CLI with --analyze --verbose and capture stdout
    main(["id3", "test_data/dummy.mp3", "--analyze", "--verbose"])
    out = capsys.readouterr().out

    assert "Proposed metadata:" in out
    assert "TXXX:provenance" in out or "TXXX:genre_top" in out
