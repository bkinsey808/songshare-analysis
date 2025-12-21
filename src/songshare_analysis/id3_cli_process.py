from __future__ import annotations
# ruff: noqa: I001

from typing import Any
from pathlib import Path

from .id3_io import read_id3
from .id3_cli_print import (
    _print_basic_info,
    _fetch_and_print_musicbrainz,
    _should_skip_mb_fetch,
)
from .id3_cli_apply import _maybe_propose_and_apply


def _process_file(f: Path, args: Any, logger: Any) -> dict[str, object]:
    """Process a single file and return the result dict from
    `_maybe_propose_and_apply` or a default when nothing happened.
    """
    try:
        info = read_id3(f)
    except Exception as exc:  # pragma: no cover - simple error path
        logger.error("Failed to read tags from %s: %s", str(f), exc)
        return {"applied": False, "embed": None}

    tags = _print_basic_info(info, logger, getattr(args, "verbose", False))

    if not (
        getattr(args, "fetch_metadata", False)
        or getattr(args, "fetch-metadata", False)
    ):
        return {"applied": False, "embed": None}

    if getattr(args, "mb_fetch_missing", False) and _should_skip_mb_fetch(tags):
        if getattr(args, "verbose", False):
            logger.info("Skipping MusicBrainz lookup (tags present)")
        return {"applied": False, "embed": None}

    mb_info = _fetch_and_print_musicbrainz(
        tags, logger, getattr(args, "verbose", False)
    )
    if not mb_info:
        return {"applied": False, "embed": None}

    return _maybe_propose_and_apply(f, args, logger, mb_info)


def _process_all_files(
    files: list[Path], args: Any, logger: Any
) -> tuple[int, int, int, int]:
    """Process a list of files and return counters (processed, applied,
    embedded, failed)."""
    files_processed = 0
    tags_applied = 0
    covers_embedded = 0
    covers_failed = 0

    for f in files:
        files_processed += 1
        res = _process_file(f, args, logger)
        if res.get("applied"):
            tags_applied += 1
        emb = res.get("embed")
        if emb is True:
            covers_embedded += 1
        elif emb is False:
            covers_failed += 1

    return files_processed, tags_applied, covers_embedded, covers_failed


def _iter_audio_files(path: Path, recursive: bool) -> list[Path]:
    """Return a list of audio files at `path`. If `path` is a file, return it.

    When `recursive` is True and `path` is a directory, walk subdirectories
    recursively and accumulate candidate audio files by suffix.
    """
    suffixes = {".mp3", ".mp4", ".m4a", ".flac", ".wav", ".ogg"}

    # If this looks like a file, just return it (even if it doesn't exist).
    # This preserves backward compatibility with callers that pass a filename
    # which may not be present during unit tests (we rely on monkeypatched
    # read_id3 behavior in tests).
    if path.is_file() or not path.exists():
        return [path]

    out: list[Path] = []
    if recursive:
        for dirpath, _, filenames in __import__("os").walk(str(path)):
            d = Path(dirpath)
            for fn in filenames:
                p = d / fn
                if p.suffix.lower() in suffixes:
                    out.append(p)
    else:
        for p in path.iterdir():
            if p.is_file() and p.suffix.lower() in suffixes:
                out.append(p)
    return out


def handle_id3_command(args: Any, logger: Any) -> None:
    """Handle the `id3` subcommand using the provided parsed args.

    Supports operating on a single file or a directory (with optional
    recursive scanning).
    """
    p = Path(args.path)
    try:
        files = _iter_audio_files(p, getattr(args, "recursive", False))
    except Exception as exc:  # pragma: no cover - simple error path
        logger.error("Invalid path %s: %s", args.path, exc)
        return

    if not files:
        logger.info("No audio files found at %s", args.path)
        return

    # Counters for a final summary
    files_processed = 0
    tags_applied = 0
    covers_embedded = 0
    covers_failed = 0

    # Use module-level helpers to process files
    files_processed, tags_applied, covers_embedded, covers_failed = (
        _process_all_files(files, args, logger)
    )

    # Emit a concise summary
    logger.info(
        "Processed %d files: tags applied=%d, covers embedded=%d, covers failed=%d",
        files_processed,
        tags_applied,
        covers_embedded,
        covers_failed,
    )
