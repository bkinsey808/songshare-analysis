from pathlib import Path
from typing import Any

import pytest

from songshare_analysis.__main__ import main


def _fake_read_id3(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tags": {"TIT2": "SongTitle", "TPE1": "ArtistName"},
        "info": {"length": 123},
    }


def _fake_musicbrainz_lookup(tags: dict[str, Any]) -> dict[str, str]:
    return {"recording_title": "Found"}


def _fake_propose_metadata_from_mb(mb: dict[str, Any]) -> dict[str, str]:
    return {"TIT2": "NewTitle"}


def test_cli_id3_prints_tags(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--verbose"])

    assert any("File:" in r.getMessage() for r in caplog.records)
    assert any("Tags:" in r.getMessage() for r in caplog.records)
    assert any("TIT2" in r.getMessage() for r in caplog.records)
    assert any("TPE1" in r.getMessage() for r in caplog.records)


def test_cli_id3_fetch_metadata(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_musicbrainz_lookup)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--fetch-metadata", "--verbose"])

    assert any("MusicBrainz" in r.getMessage() for r in caplog.records)
    assert any(
        "recording_title" in r.getMessage() or "Found" in r.getMessage()
        for r in caplog.records
    )


def test_cli_id3_directory_scan(
    tmp_path: Path, monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    # Create files and a subdirectory with another file
    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"")
    sub = tmp_path / "sub"
    sub.mkdir()
    f2 = sub / "b.mp3"
    f2.write_bytes(b"")

    # Fake read_id3 to simply echo path
    def echo_read(path: Path) -> dict[str, Any]:
        return {"path": str(path), "tags": {"TIT2": "X"}, "info": {}}

    import songshare_analysis.id3_cli_process as id3_process

    monkeypatch.setattr(id3_process, "read_id3", echo_read)

    # Non-recursive scan should only see top-level file
    caplog.set_level(logging.INFO)
    main(["id3", str(tmp_path), "--verbose"])

    assert any(str(f1) in r.getMessage() for r in caplog.records)
    assert not any(str(f2) in r.getMessage() for r in caplog.records)


def test_cli_id3_directory_scan_recursive(
    tmp_path: Path, monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    # Create files and a subdirectory with another file
    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"")
    sub = tmp_path / "sub"
    sub.mkdir()
    f2 = sub / "b.mp3"
    f2.write_bytes(b"")

    # Fake read_id3 to simply echo path
    def echo_read(path: Path) -> dict[str, Any]:
        return {"path": str(path), "tags": {"TIT2": "X"}, "info": {}}

    import songshare_analysis.id3_cli_process as id3_process

    monkeypatch.setattr(id3_process, "read_id3", echo_read)

    # Recursive scan should include subdirectory file
    caplog.set_level(logging.INFO)
    main(["id3", str(tmp_path), "--recursive", "--verbose"])

    assert any(str(f1) in r.getMessage() for r in caplog.records)
    assert any(str(f2) in r.getMessage() for r in caplog.records)


def test_cli_id3_apply_metadata_yes_invokes_apply(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    import songshare_analysis.id3_cli_apply as id3_apply
    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)
    monkeypatch.setattr(id3mb, "musicbrainz_lookup", _fake_musicbrainz_lookup)
    monkeypatch.setattr(
        id3_apply, "propose_metadata_from_mb", _fake_propose_metadata_from_mb
    )

    called: dict[str, Any] = {}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True
        called["path"] = str(path)
        called["proposed"] = proposed

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    main(["id3", "dummy.mp3", "--fetch-metadata", "--apply-metadata", "--yes"])

    assert called.get("applied")
    assert called.get("proposed") == {"TIT2": "NewTitle"}


def test_cli_fetch_print_hides_binary(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)

    def fake_mb(tags: dict[str, Any]) -> dict[str, Any]:
        return {"cover_art": b"\xff\xff" * 50, "recording_title": "Found"}

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb)

    caplog.set_level(logging.INFO)
    main(["id3", "dummy.mp3", "--fetch-metadata", "--verbose"])

    assert any("<binary data" in r.getMessage() for r in caplog.records)
    # raw bytes shouldn't be logged
    assert not any("\xff" in r.getMessage() for r in caplog.records)


def test_cli_embed_failure_skips_apply(
    monkeypatch: Any, caplog: pytest.LogCaptureFixture
) -> None:
    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)

    # Ensure MB info includes a cover_art URL so embedding is attempted
    def fake_mb_with_cover(tags: dict[str, Any]) -> dict[str, Any]:
        d = _fake_musicbrainz_lookup(tags).copy()
        d["cover_art"] = "https://example.com/cover.jpg"
        return d

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb_with_cover)
    # Patch id3mb and also the bound name used by the CLI module
    monkeypatch.setattr(
        id3mb,
        "propose_metadata_from_mb",
        _fake_propose_metadata_from_mb,
    )
    import songshare_analysis.id3_cli_apply as id3_apply

    monkeypatch.setattr(
        id3_apply,
        "propose_metadata_from_mb",
        _fake_propose_metadata_from_mb,
    )

    # Simulate embed failing
    import songshare_analysis.id3_cover as id3mod

    monkeypatch.setattr(id3mod, "_embed_cover_if_needed", lambda p, u: False)

    called: dict[str, Any] = {}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    import songshare_analysis.id3_cli_apply as id3_apply

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    # Should not raise; apply should NOT be called if embedding fails
    main(
        [
            "id3",
            "dummy.mp3",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
            "--verbose",
        ]
    )

    expected = "Cover art embedding failed; skipping metadata apply for this file."
    assert any(expected in r.getMessage() for r in caplog.records)
    assert not called.get("applied")


def test_cli_embed_skipped_applies(monkeypatch: Any) -> None:
    import songshare_analysis.id3_cli_process as id3_process
    import songshare_analysis.id3_mb as id3mb

    monkeypatch.setattr(id3_process, "read_id3", _fake_read_id3)

    # Ensure MB info includes a cover_art URL so embedding is attempted
    def fake_mb_with_cover(tags: dict[str, Any]) -> dict[str, Any]:
        d = _fake_musicbrainz_lookup(tags).copy()
        d["cover_art"] = "https://example.com/cover.jpg"
        return d

    monkeypatch.setattr(id3mb, "musicbrainz_lookup", fake_mb_with_cover)
    monkeypatch.setattr(
        id3mb,
        "propose_metadata_from_mb",
        _fake_propose_metadata_from_mb,
    )
    import songshare_analysis.id3_cli_apply as id3_apply

    monkeypatch.setattr(
        id3_apply,
        "propose_metadata_from_mb",
        _fake_propose_metadata_from_mb,
    )

    # Simulate embed skipped (already has art)
    import songshare_analysis.id3_cover as id3mod

    monkeypatch.setattr(id3mod, "_embed_cover_if_needed", lambda p, u: None)

    called: dict[str, Any] = {}

    def fake_apply(path: Path, proposed: dict[str, str]) -> None:
        called["applied"] = True

    import songshare_analysis.id3_cli_apply as id3_apply

    monkeypatch.setattr(id3_apply, "apply_metadata", fake_apply)

    # Should proceed to apply even though embedding was skipped
    main(
        [
            "id3",
            "dummy.mp3",
            "--fetch-metadata",
            "--apply-metadata",
            "--yes",
            "--embed-cover-art",
        ]
    )

    assert called.get("applied")

    assert called.get("applied")

    assert called.get("applied")
    assert called.get("applied")
