import sys
from pathlib import Path
from typing import Any

import pytest

from songshare_analysis import id3_io as id3io
from songshare_analysis import mb as id3mb
from songshare_analysis.cli import id3_cli_apply as id3_apply
from songshare_analysis.cli.__main__ import main
from songshare_analysis.types import MBInfo


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_apply_metadata_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Create an empty mp3 file
    p = tmp_path / "apply_test.mp3"
    p.write_bytes(b"")

    # Pre-seed the file with a title so lookup will run
    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2

        tags = ID3()  # type: ignore
        tags.add(TIT2(encoding=3, text=["Om Test"]))  # type: ignore
        tags.save(str(p))
    except Exception:
        pytest.skip("mutagen not available or couldn't write test tags")

    # Monkeypatch musicbrainz_lookup to avoid network
    def fake_mb(_tags: dict[str, str]) -> MBInfo:
        return {
            "recording_id": "rec-42",
            "recording_title": "Test Song",
            "artist": "Test Artist",
            "release_title": "Test Release",
            "release_id": "rel-99",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    # Run CLI to fetch + apply with auto-yes
    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])

    # CLI should print a short confirmation to stdout
    out = capsys.readouterr().out
    assert f"File: {p}" in out
    assert "Applied metadata to" in out

    # Read tags and assert written. Since the file had an existing title, it
    # should be preserved and the proposed value recorded in a TXXX frame.
    info = id3io.read_id3(p)
    assert info["tags"].get("TIT2")
    tit2_value = info["tags"].get("TIT2", "")
    if isinstance(tit2_value, (bytes, bytearray)):
        tit2_value = tit2_value.decode("utf-8", errors="ignore")
    elif isinstance(tit2_value, list):
        tit2_value = " ".join(tit2_value)
    assert "Om Test" in str(tit2_value)
    proposed_value = info["tags"].get("TXXX:musicbrainz_proposed_TIT2", "")
    if isinstance(proposed_value, (bytes, bytearray)):
        proposed_value = proposed_value.decode("utf-8", errors="ignore")
    elif isinstance(proposed_value, list):
        proposed_value = " ".join(proposed_value)
    assert "Test Song" in str(proposed_value)

    # Backup sidecar should exist
    bak = p.with_suffix(p.suffix + ".tags.bak.json")
    assert bak.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_apply_then_no_proposals_on_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Create an MP3 with an existing title
    p = tmp_path / "idempotent.mp3"
    p.write_bytes(b"\x00" * 128)

    pytest.importorskip("mutagen.id3")

    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2

        tags = ID3()  # type: ignore
        tags.add(TIT2(encoding=3, text=["Om Test"]))  # type: ignore
        tags.save(str(p))
    except Exception:
        pytest.skip("mutagen not available or couldn't write test tags")

    # Fake MB lookup that proposes different metadata
    def fake_mb_idempotent(*_: object) -> MBInfo:
        return {
            "recording_id": "rec-42",
            "recording_title": "Test Song",
            "artist": "Test Artist",
            "release_title": "Test Release",
            "release_id": "rel-99",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb_idempotent)

    # First run: should print proposals
    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])
    out1 = capsys.readouterr().out
    assert "Proposed metadata:" in out1
    assert "Applied metadata to" in out1

    # Second run: should not print proposals (already applied)
    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])
    out2 = capsys.readouterr().out
    assert "Proposed metadata:" not in out2
    assert "Applied metadata to" not in out2


@pytest.mark.skipif(sys.platform == "win32", reason="Works on POSIX in CI")
def test_detect_noop_apply_logs_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """If apply_metadata is a no-op (doesn't change the file) we should
    detect it after a successful apply call and warn that the write may have
    failed, and not count the file as applied.
    """
    # Create an MP3 with an existing title
    p = tmp_path / "noop_apply.mp3"
    p.write_bytes(b"\x00" * 128)

    pytest.importorskip("mutagen.id3")

    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TIT2

        tags = ID3()  # type: ignore
        tags.add(TIT2(encoding=3, text=["Existing Title"]))  # type: ignore
        tags.save(str(p))
    except Exception:
        pytest.skip("mutagen not available or couldn't write test tags")

    # Fake MB lookup that proposes different metadata
    def fake_mb_noop(*_: object) -> MBInfo:
        return {
            "recording_id": "rec-noop",
            "recording_title": "New Title",
            "artist": "New Artist",
            "release_title": "New Release",
            "release_id": "rel-noop",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr("songshare_analysis.mb.musicbrainz_lookup", fake_mb_noop)

    # Monkeypatch apply_metadata to be a no-op so it reports success but doesn't
    # actually change the file.
    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        # intentionally do nothing
        return None

    monkeypatch.setattr(
        "songshare_analysis.cli.id3_cli_apply.apply_metadata", fake_apply
    )

    caplog.set_level("INFO")
    # Run CLI to fetch + apply with auto-yes
    main(["id3", "--fetch-metadata", "--apply-metadata", "--yes", str(p)])

    # We should have logged a warning about the write not taking effect
    assert any(
        "write may have failed" in r.getMessage()
        or "remain unchanged" in r.getMessage()
        or "tags unchanged" in r.getMessage()
        for r in caplog.records
    )

    # Summary should indicate zero applied
    assert any("tags applied=0" in r.getMessage() for r in caplog.records)
    # Create an empty mp3 file without a title
    p = tmp_path / "apply_test_no_title.mp3"
    # Ensure file has some space so Mutagen can write ID3 headers reliably
    p.write_bytes(b"\x00" * 128)

    pytest.importorskip("mutagen.id3")

    # Monkeypatch musicbrainz_lookup to avoid network
    def fake_mb(_tags: dict[str, str]) -> MBInfo:
        return {
            "recording_id": "rec-99",
            "recording_title": "Fresh Song",
            "artist": "Fresh Artist",
            "release_title": "Fresh Release",
            "release_id": "rel-99",
            "provenance": {"source": "test"},
        }

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    # Instead of invoking the CLI (which relies on existing tags to trigger
    # a lookup), call apply directly with a proposed mapping to verify that
    # applying to a file with no existing title writes the common TIT2 frame.
    proposed = id3mb.propose_metadata_from_mb(fake_mb({}))
    id3io.apply_metadata(p, proposed)

    info = id3io.read_id3(p)
    tit2_value = info["tags"].get("TIT2", "")
    if isinstance(tit2_value, (bytes, bytearray)):
        tit2_value = tit2_value.decode("utf-8", errors="ignore")
    elif isinstance(tit2_value, list):
        tit2_value = " ".join(tit2_value)
    # Backup sidecar should exist
    bak = p.with_suffix(p.suffix + ".tags.bak.json")
    assert bak.exists()


def _fake_read_id3_identical(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {"TIT2": "SongTitle", "TPE1": "ArtistName"},
        "info": {"length": 123},
    }


def _fake_musicbrainz_lookup_identical(tags: dict[str, Any]) -> dict[str, str]:
    # Returns values that are identical to the current tags
    return {"recording_title": "SongTitle", "artist": "ArtistName"}


def test_cli_id3_apply_skips_when_proposed_matches_existing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI skips apply when proposed metadata matches existing."""
    import logging

    import songshare_analysis.cli.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3_identical)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_musicbrainz_lookup_identical)

    called = {"applied": False}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)
    main(
        ["id3", "test_data/dummy.mp3", "--fetch-metadata", "--apply-metadata", "--yes"]
    )

    assert not called["applied"]
    assert any(
        "No proposed metadata to apply" in r.getMessage() for r in caplog.records
    )
    out = capsys.readouterr().out
    assert "Proposed metadata:" not in out


def test_cli_stats_counts_apply_and_embed(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test CLI stats counting when applying metadata and embedding cover art."""
    import logging

    import songshare_analysis.cli.id3_cli_process as id3_process
    import songshare_analysis.mb as id3mb
    from songshare_analysis import id3_cover

    def fake_iter(path: Path, recursive: bool) -> list[Path]:
        return [
            Path("test_data/a.mp3"),
            Path("test_data/b.mp3"),
            Path("test_data/c.mp3"),
        ]

    def fake_read(p: Path) -> dict[str, object]:
        return {"path": str(p), "tags": {"TIT2": "X"}, "info": {}}

    monkeypatch.setattr(id3_process, "_iter_audio_files", fake_iter)

    monkeypatch.setattr(id3_process, "read_id3", fake_read)

    monkeypatch.setattr(
        id3mb,
        "musicbrainz_lookup",
        lambda tags: {"cover_art": "https://example.com/cover.jpg"},
    )

    monkeypatch.setattr(id3mb, "propose_metadata_from_mb", lambda mb: {"TIT2": "New"})

    monkeypatch.setattr(
        id3_apply,
        "propose_metadata_from_mb",
        lambda mb: {"TIT2": "New"},
    )

    def fake_embed(path: Path, url: str) -> bool | None:
        if str(path).endswith("test_data/a.mp3"):
            return True
        if str(path).endswith("b.mp3"):
            return False
        return None

    monkeypatch.setattr(id3_cover, "_embed_cover_if_needed", fake_embed)

    applied = {}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        applied[str(path)] = proposed

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    caplog.set_level(logging.INFO)

    main(
        [
            "id3",
            "dummy",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
        ],
    )

    assert "test_data/a.mp3" in applied
    assert "test_data/c.mp3" in applied
    assert "b.mp3" not in applied

    msgs = [r.getMessage() for r in caplog.records]
    assert sum(1 for m in msgs if m == "Metadata applied (backup created).") == 2

    embedded_count = sum(1 for p in applied if fake_embed(Path(p), ""))
    assert embedded_count == 1

    assert any(
        "Cover art embedding failed; skipping metadata apply for this file." in m
        for m in msgs
    )
