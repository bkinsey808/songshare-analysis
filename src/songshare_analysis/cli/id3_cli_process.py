from __future__ import annotations

from logging import Logger
from pathlib import Path
from typing import Protocol

from songshare_analysis.id3_io import read_id3

from .id3_cli_apply import _maybe_propose_and_apply
from .id3_cli_print import (
    _fetch_and_print_musicbrainz,
    _print_basic_info,
    _should_skip_mb_fetch,
)


class ProcessArgs(Protocol):
    """Protocol for parsed CLI args used by processing helpers."""

    path: str
    recursive: bool | None
    fetch_metadata: bool | None
    mb_fetch_missing: bool | None
    verbose: bool | None

    # Also include options forwarded to apply helpers
    apply_metadata: bool | None
    embed_cover_art: bool | None
    yes: bool | int | None


def _process_file(
    f: Path,
    args: ProcessArgs,
    logger: Logger,
) -> dict[str, bool | None]:
    """Process a single file and return the result dict from
    `_maybe_propose_and_apply` or a default when nothing happened.
    """
    try:
        info = read_id3(f)
    except Exception:  # pragma: no cover - simple error path
        logger.exception("Failed to read tags from %s", str(f))
        return {"applied": False, "embed": None}

    tags = _print_basic_info(info, logger, getattr(args, "verbose", False))

    if not (
        getattr(args, "fetch_metadata", False) or getattr(args, "fetch-metadata", False)
    ):
        return {"applied": False, "embed": None}

    # If the file already contains explicit MusicBrainz IDs, skip the
    # lookup entirely and do not propose MusicBrainz-derived metadata. This
    # avoids unnecessary network calls and prevents overriding existing MB
    # provenance.
    if tags.get("TXXX:musicbrainz_recording_id") or tags.get(
        "TXXX:musicbrainz_release_id"
    ):
        # Silent skip when MusicBrainz IDs are already present; do not perform a
        # lookup and do not emit any log or stdout output for this case. Return
        # a `skipped` flag so callers can aggregate statistics.
        return {"applied": False, "embed": None, "skipped": True}

    if getattr(args, "mb_fetch_missing", False) and _should_skip_mb_fetch(tags):
        if getattr(args, "verbose", False):
            logger.info("Skipping MusicBrainz lookup (tags present)")
        return {"applied": False, "embed": None}

    mb_info = _fetch_and_print_musicbrainz(
        tags,
        logger,
        getattr(args, "verbose", False),
    )
    if not mb_info:
        return {"applied": False, "embed": None}

    # Pass the current tags through so `_maybe_propose_and_apply` can
    # determine whether any proposed fields would actually change the file.
    return _maybe_propose_and_apply(f, args, logger, mb_info, tags)


def _process_all_files(
    files: list[Path],
    args: ProcessArgs,
    logger: Logger,
) -> tuple[int, int, int, int, int]:
    """Process a list of files and return counters (processed, applied,
    embedded, failed, skipped).
    """
    files_processed = 0
    tags_applied = 0
    covers_embedded = 0
    covers_failed = 0
    files_skipped = 0

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
        if res.get("skipped"):
            files_skipped += 1

    return files_processed, tags_applied, covers_embedded, covers_failed, files_skipped


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


def handle_id3_command(args: ProcessArgs, logger: Logger) -> None:
    """Handle the `id3` subcommand using the provided parsed args.

    Supports operating on a single file or a directory (with optional
    recursive scanning).
    """
    p = Path(args.path)
    try:
        files = _iter_audio_files(p, getattr(args, "recursive", False))
    except Exception:  # pragma: no cover - simple error path
        logger.exception("Invalid path %s", args.path)
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
    (
        files_processed,
        tags_applied,
        covers_embedded,
        covers_failed,
        files_skipped,
    ) = _process_all_files(files, args, logger)

    # Emit a concise summary with skipped files counter
    logger.info(
        "Processed %d files: tags applied=%d, files skipped=%d, \n"
        "covers embedded=%d, covers failed=%d",
        files_processed,
        tags_applied,
        files_skipped,
        covers_embedded,
        covers_failed,
    )

    # Also print a brief summary to stdout so users see it even without
    # --verbose (INFO logs require --verbose to be visible by default).
    summary_str = (
        f"Processed {files_processed} files: tags applied={tags_applied}, "
        f"files skipped={files_skipped}, covers embedded={covers_embedded}, "
        f"covers failed={covers_failed}"
    )
    print(summary_str)  # noqa: T201
