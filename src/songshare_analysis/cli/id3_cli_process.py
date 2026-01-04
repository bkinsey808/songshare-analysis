from __future__ import annotations

from logging import Logger
from pathlib import Path
from typing import Protocol

from songshare_analysis.essentia import analysis_to_id3, essentia_extractor
from songshare_analysis.id3_io import read_id3

from .id3_cli_apply import _maybe_propose_and_apply
from .id3_cli_apply_helpers import _compute_delta, _confirm_apply, _verify_apply_result
from .id3_cli_print import (
    _fetch_and_print_musicbrainz,
    _print_basic_info,
    _print_proposed_metadata,
    _should_skip_mb_fetch,
)


class ProcessArgs(Protocol):
    """Protocol for parsed CLI args used by processing helpers."""

    path: str
    recursive: bool | None
    fetch_metadata: bool | None
    mb_fetch_missing: bool | None
    verbose: bool | None

    # Essentia flags
    analyze: bool | None
    apply_tags: bool | None
    separate_vocals: bool | None

    # Also include options forwarded to apply helpers
    apply_metadata: bool | None
    embed_cover_art: bool | None
    yes: bool | int | None


def _write_basic_sidecar(f: Path, logger: Logger, verbose: bool | None = False) -> dict:
    """Extract basic and semantic analysis and write a sidecar.

    This consolidates duplicated logic used when rhythm timing detection is
    skipped (tags already present) or when the full analysis path is used.
    """
    analysis = essentia_extractor.extract_basic(f)
    try:
        sem = essentia_extractor.extract_semantic(f)
        if sem and isinstance(sem, dict):
            analysis.update(sem)
    except Exception:
        pass
    sidecar = essentia_extractor.write_analysis_sidecar(f, analysis)
    if verbose:
        logger.info("Wrote Essentia sidecar: %s", str(sidecar))
    return analysis


def _maybe_run_analysis(
    f: Path, args: ProcessArgs, logger: Logger, tags: dict | None = None
) -> None:
    """Run Essentia analysis and write sidecar when requested.

    If rhythm tags are already present on the file (for example,
    `TXXX:rhythm_timing`, `TXXX:rhythm_human`, or `TXXX:rhythm_machine`),
    skip beat timing detection to avoid overwriting user-set tags.
    """
    if not getattr(args, "analyze", False):
        return

    # If tags indicate rhythm timing is already present, skip rhythm detection
    existing_rhythm_keys = {
        "TXXX:rhythm_timing",
        "TXXX:rhythm_human",
        "TXXX:rhythm_machine",
    }
    if tags and any(k in tags for k in existing_rhythm_keys):
        if getattr(args, "verbose", False):
            logger.info("Skipping rhythm timing detection; tags already present")
        try:
            _write_basic_sidecar(f, logger, getattr(args, "verbose", False))
            return
        except Exception as exc:  # pragma: no cover - runtime
            logger.exception("Essentia analysis failed for %s: %s", str(f), exc)
            return

    # Normal path: run full analysis including rhythm timing detection
    try:
        analysis = _write_basic_sidecar(f, logger, getattr(args, "verbose", False))

        # Optionally augment analysis with rhythm timing detection
        try:
            from songshare_analysis.essentia import rhythm as rhythm_mod

            beats = analysis.get("analysis", {}).get("rhythm", {}).get("beats", [])
            if beats:
                timing = rhythm_mod.detect_rhythm_timing_from_beats(beats)
                # Merge timing results under the rhythm block for downstream use
                analysis.setdefault("analysis", {})
                analysis["analysis"].setdefault("rhythm", {})
                analysis["analysis"]["rhythm"]["timing"] = timing
        except Exception:
            # Non-fatal: keep basic analysis even if rhythm detection fails
            pass

        if getattr(args, "verbose", False):
            try:
                proposed = analysis_to_id3(analysis)
                _print_proposed_metadata(proposed)
            except Exception:
                logger.exception("Failed to compute/print proposed metadata")
    except Exception as exc:  # pragma: no cover - runtime
        logger.exception("Essentia analysis failed for %s: %s", str(f), exc)


def _apply_analysis_tags(
    f: Path, args: ProcessArgs, logger: Logger, tags: dict
) -> dict[str, bool | None]:
    """Convert analysis to ID3 tags and apply them if confirmed."""
    try:
        analysis = essentia_extractor.read_sidecar(f)
        if analysis is None:
            analysis = essentia_extractor.extract_basic(f)

        # Optionally augment analysis with rhythm timing detection if beats are
        # present (so applying tags behaves like running `--analyze`). This
        # mirrors the augmentation performed by `_maybe_run_analysis`.
        try:
            from songshare_analysis.essentia import rhythm as rhythm_mod

            beats = analysis.get("analysis", {}).get("rhythm", {}).get("beats", [])
            if beats:
                timing = rhythm_mod.detect_rhythm_timing_from_beats(beats)
                analysis.setdefault("analysis", {})
                analysis["analysis"].setdefault("rhythm", {})
                analysis["analysis"]["rhythm"]["timing"] = timing
        except Exception:
            # Non-fatal: keep basic analysis even if rhythm detection fails
            pass

        proposed = analysis_to_id3(analysis)
        delta = _compute_delta(proposed, tags)
        if not delta:
            if getattr(args, "verbose", False):
                logger.info("No analysis-derived tags to apply for %s", str(f))
            return {"applied": False, "embed": None}

        print(f"File: {f}")  # noqa: T201
        _print_proposed_metadata(delta)

        if not _confirm_apply(args):
            print("Aborted; no changes made.")  # noqa: T201
            return {"applied": False, "embed": None}

        # Import at call-time so tests can monkeypatch `_apply_metadata_safe` on
        # the `id3_cli_apply` module and have the change picked up here.
        from .id3_cli_apply import _apply_metadata_safe as _apply_func

        applied_ok = _apply_func(f, proposed, logger)
        applied = False
        if applied_ok:
            verified = _verify_apply_result(f, proposed, logger)
            applied = bool(verified)
        return {"applied": applied, "embed": None}
    except Exception as exc:  # pragma: no cover - runtime
        logger.exception("Failed to apply analysis tags for %s: %s", str(f), exc)
        return {"applied": False, "embed": None}


def _process_file(
    f: Path,
    args: ProcessArgs,
    logger: Logger,
) -> dict[str, bool | None]:
    """Process a single file and return the result dict from
    `_maybe_propose_and_apply` or a default when nothing happened.

    Returns a dict that may include `rhythm_timing` when analysis ran and
    produced timing results.
    """
    try:
        info = read_id3(f)
    except Exception:  # pragma: no cover - simple error path
        logger.exception("Failed to read tags from %s", str(f))
        return {"applied": False, "embed": None}

    tags = _print_basic_info(info, logger, getattr(args, "verbose", False))

    # If no action requested, exit early
    if not (
        getattr(args, "fetch_metadata", False)
        or getattr(args, "fetch-metadata", False)
        or getattr(args, "analyze", False)
        or getattr(args, "apply_tags", False)
    ):
        return {"applied": False, "embed": None}

    # If requested, run Essentia analysis and write a sidecar
    timing = _maybe_run_analysis(f, args, logger, tags)

    # If apply-tags requested, convert analysis to ID3 and propose/apply
    if getattr(args, "apply_tags", False):
        res = _apply_analysis_tags(f, args, logger, tags)
        # propagate rhythm timing info if present
        if timing is not None:
            res["rhythm_timing"] = timing
        return res
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


def _process_files_and_aggregate(
    files: list[Path],
    args: ProcessArgs,
    logger: Logger,
) -> dict:
    """Process files and return a counters dict summarizing results.

    This function contains the bulk of the per-file branching and aggregation
    so that `_process_all_files` itself stays short and easy to reason about.
    """
    counters = {
        "files_processed": 0,
        "tags_applied": 0,
        "covers_embedded": 0,
        "covers_failed": 0,
        "files_skipped": 0,
        "covers_already_present": 0,
        "covers_download_attempted": 0,
        "covers_download_success": 0,
        "tit2_changed": 0,
        # rhythm stats
        "rhythm_detected": 0,
        "rhythm_human": 0,
        "rhythm_clicktrack": 0,
        "rhythm_uncertain": 0,
        "beat_cv_sum": 0.0,
        "beat_cv_count": 0,
    }

    non_verbose = not getattr(args, "verbose", False)

    for f in files:
        counters["files_processed"] += 1
        inc = _process_single_file(f, args, logger, non_verbose)
        for k, v in inc.items():
            counters[k] += v

    return counters


def _file_result_to_counters(res: dict) -> dict:
    """Convert a single file processing result into per-file counter increments."""
    c = {
        "tags_applied": 1 if res.get("applied") else 0,
        "covers_embedded": 1 if res.get("embed") is True else 0,
        "covers_failed": 1 if res.get("embed") is False else 0,
        "files_skipped": 1 if res.get("skipped") else 0,
        "covers_already_present": 1 if res.get("cover_already_present") else 0,
        "covers_download_attempted": (1 if res.get("cover_download_attempted") else 0),
        "covers_download_success": 1 if res.get("cover_download_success") else 0,
        "tit2_changed": 1 if res.get("tit2_changed") else 0,
        "rhythm_detected": 0,
        "rhythm_human": 0,
        "rhythm_clicktrack": 0,
        "rhythm_uncertain": 0,
        "beat_cv_sum": 0.0,
        "beat_cv_count": 0,
    }
    timing = res.get("rhythm_timing")
    if isinstance(timing, dict):
        c["rhythm_detected"] = 1
        label = timing.get("label")
        if label == "human":
            c["rhythm_human"] = 1
        elif label == "clicktrack":
            c["rhythm_clicktrack"] = 1
        else:
            c["rhythm_uncertain"] = 1
        beat_cv = timing.get("beat_cv")
        try:
            if beat_cv is not None:
                c["beat_cv_sum"] = float(beat_cv)
                c["beat_cv_count"] = 1
        except Exception:
            pass
    return c


def _safe_read_sidecar(path: Path):
    try:
        return essentia_extractor.read_sidecar(path)
    except Exception:
        return None


def _print_file_summary(
    path: Path,
    res: dict,
    sidecar_changed: bool,
    non_verbose: bool,
) -> None:
    if not non_verbose:
        return
    # Compute cover status
    cover_status = "none"
    if res.get("cover_already_present"):
        cover_status = "already-present"
    elif res.get("embed") is True:
        cover_status = "embedded"
    elif res.get("embed") is False:
        cover_status = "embed-failed"

    tags_status = "applied" if res.get("applied") else "unchanged"
    json_status = "updated" if sidecar_changed else "unchanged"

    print(f"Processing: {path}")  # noqa: T201
    print(f"  Cover: {cover_status}")  # noqa: T201
    print(f"  Tags: {tags_status}")  # noqa: T201
    print(f"  Sidecar: {json_status}")  # noqa: T201


def _process_single_file(
    path: Path,
    args: ProcessArgs,
    logger: Logger,
    non_verbose: bool,
) -> dict:
    """Process a single file and return counter increments dict.

    This extracts the per-file branching so `_process_files_and_aggregate`
    itself stays small and easy to reason about (reduces McCabe complexity).
    """
    pre_sidecar = _safe_read_sidecar(path)
    res = _process_file(path, args, logger)
    post_sidecar = _safe_read_sidecar(path)
    sidecar_changed = pre_sidecar != post_sidecar
    _print_file_summary(path, res, sidecar_changed, non_verbose)
    return _file_result_to_counters(res)


def _process_all_files(
    files: list[Path],
    args: ProcessArgs,
    logger: Logger,
) -> tuple[
    int, int, int, int, int, int, int, int, int, int, int, int, int, float | None
]:
    """Process a list of files and return counters.

    Returns a tuple with the existing counters followed by rhythm stats:
    (processed, applied, embedded, failed, skipped, already_present,
     download_attempted, download_success, tit2_changed,
     rhythm_detected, rhythm_human, rhythm_clicktrack, rhythm_uncertain,
     avg_beat_cv_or_None)
    """
    counters = _process_files_and_aggregate(files, args, logger)

    avg_beat_cv: float | None = None
    if counters["beat_cv_count"] > 0:
        avg_beat_cv = counters["beat_cv_sum"] / counters["beat_cv_count"]

    return (
        counters["files_processed"],
        counters["tags_applied"],
        counters["covers_embedded"],
        counters["covers_failed"],
        counters["files_skipped"],
        counters["covers_already_present"],
        counters["covers_download_attempted"],
        counters["covers_download_success"],
        counters["tit2_changed"],
        counters["rhythm_detected"],
        counters["rhythm_human"],
        counters["rhythm_clicktrack"],
        counters["rhythm_uncertain"],
        avg_beat_cv,
    )


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
    files_skipped = 0
    covers_already_present = 0
    covers_download_attempted = 0
    covers_download_success = 0
    tit2_changed = 0

    # Use module-level helpers to process files
    (
        files_processed,
        tags_applied,
        covers_embedded,
        covers_failed,
        files_skipped,
        covers_already_present,
        covers_download_attempted,
        covers_download_success,
        tit2_changed,
        rhythm_detected,
        rhythm_human,
        rhythm_clicktrack,
        rhythm_uncertain,
        avg_beat_cv,
    ) = _process_all_files(files, args, logger)

    # Emit a concise summary with skipped files counter
    logger.info(
        "Processed %d files: tags applied=%d, files skipped=%d, \n"
        "covers embedded=%d, covers failed=%d, covers already present=%d, \n"
        "cover downloads attempted=%d, cover downloads successful=%d, \n"
        "TIT2 changed=%d",
        files_processed,
        tags_applied,
        files_skipped,
        covers_embedded,
        covers_failed,
        covers_already_present,
        covers_download_attempted,
        covers_download_success,
        tit2_changed,
    )

    # Also print a brief summary to stdout so users see it even without
    # --verbose (INFO logs require --verbose to be visible by default).
    summary_str = (
        f"Processed files: {files_processed}\n"
        f"Files skipped: {files_skipped}\n"
        f"Tags applied: {tags_applied}\n"
        f"Covers embedded: {covers_embedded}\n"
        f"Covers failed: {covers_failed}\n"
        f"Covers already present: {covers_already_present}\n"
        f"Cover downloads attempted: {covers_download_attempted}\n"
        f"Cover downloads successful: {covers_download_success}\n"
        f"TIT2 changed: {tit2_changed}\n"
        f"Rhythm detections: {rhythm_detected} (human={rhythm_human}, "
        f"clicktrack={rhythm_clicktrack}, uncertain={rhythm_uncertain})\n"
        + (f"Average beat_cv: {avg_beat_cv:.6f}\n" if avg_beat_cv is not None else "")
    )
    print(summary_str)  # noqa: T201
