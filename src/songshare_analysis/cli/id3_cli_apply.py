from __future__ import annotations

from collections.abc import Mapping
from logging import Logger
from pathlib import Path

from songshare_analysis.id3_io import apply_metadata
from songshare_analysis.mb import propose_metadata_from_mb
from songshare_analysis.types import Args, LoggerLike, MBInfo, TagValue

from .id3_cli_apply_helpers import (
    _apply_metadata_safe,
    _compute_delta,
    _confirm_apply,
    _maybe_embed_cover,
    _perform_embed,
    _prepare_embed,
    _print_apply_result,
    _print_embed_preview,
    _verify_apply_result,
)
from .id3_cli_print import _print_proposed_metadata

# Keep `apply_metadata` available at module level so tests can monkeypatch it.
# This is intentionally referenced to avoid unused-import lint issues.
assert callable(apply_metadata)  # sanity check / exported for tests

# Re-export a small set of internal helpers to preserve test expectations
__all__ = [
    "_confirm_apply",
    "_maybe_embed_cover",
    "_apply_metadata_safe",
    "apply_metadata",
]


def _maybe_propose_and_apply(
    target_path: Path,
    args: Args,
    logger: Logger | LoggerLike,
    mb_info: MBInfo | Mapping[str, object],
    existing_tags: Mapping[str, TagValue] | None = None,
) -> dict[str, bool | None]:  # noqa: PLR0911 (multiple early returns for clarity)
    """Propose metadata derived from MusicBrainz info and optionally apply it to a path.

    Only print a preview if the proposed metadata would actually add or change
    values compared to `existing_tags`.

    Returns a dict describing what happened with keys:
      - applied: bool (True if metadata was applied)
      - embed: True|False|None (embed outcome)
    """
    result = {"applied": False, "embed": None}

    apply_flag = getattr(args, "apply_metadata", False) or getattr(
        args,
        "apply-metadata",
        False,
    )
    if not apply_flag:
        return result

    proposed = propose_metadata_from_mb(mb_info)

    cover_url, _embed_requested, embed_would_write, cover_bytes = _prepare_embed(
        args,
        mb_info,
        existing_tags,
    )

    if not proposed and not embed_would_write:
        logger.info("No proposed metadata to apply")
        return result

    # Capture a snapshot of existing tags so we can report what changed later.
    before_tags = existing_tags
    if before_tags is None:
        try:
            from songshare_analysis.id3_io import read_id3

            before_tags = read_id3(target_path).get("tags", {}) or {}
        except Exception:
            before_tags = {}

    delta = _compute_delta(proposed, existing_tags)

    if not delta and not embed_would_write:
        logger.info("No proposed metadata to apply")
        return result

    # Print a short per-file header so users can see which file is being
    # proposed/changed when running in batch mode.
    print(f"File: {target_path}")  # noqa: T201

    _print_proposed_metadata(delta)

    if embed_would_write:
        _print_embed_preview(cover_url if cover_bytes is None else cover_bytes)

    if not _confirm_apply(args):
        # Intentional CLI behaviour (print to stdout) — keep for backward compatibility
        print("Aborted; no changes made.")  # noqa: T201
        return result

    # Perform embed + apply flow in a helper to keep complexity low here.
    return _perform_apply_and_report(
        target_path,
        args,
        logger,
        mb_info,
        cover_bytes,
        cover_url,
        delta,
        before_tags or {},
        proposed,
    )


def _perform_apply_and_report(
    target_path: Path,
    args: Args,
    logger: Logger | LoggerLike,
    mb_info: MBInfo | Mapping[str, object],
    cover_bytes: bytes | None,
    cover_url: str | bytes | None,
    delta: dict[str, TagValue],
    before_tags: Mapping[str, TagValue],
    proposed: dict[str, str],
) -> dict[str, bool | None]:
    """Attempt embed, apply metadata, verify and print a per-file report.

    Returns a result dict with keys ``applied`` and ``embed`` mirroring the
    previous semantics from the larger function.
    """
    result = {"applied": False, "embed": None}

    # Attempt embed first; abort apply on embed failure
    embed_result = _perform_embed(
        target_path,
        args,
        logger,
        mb_info,
        cover_bytes,
        cover_url,
    )
    result["embed"] = embed_result
    if embed_result is False:
        return result

    if not delta:
        return result

    applied_ok = _apply_metadata_safe(target_path, proposed, logger)

    if not applied_ok:
        result["applied"] = False
        return result

    # Verify write by re-reading and checking for any remaining delta.
    verified = _verify_apply_result(target_path, proposed, logger)
    result["applied"] = bool(verified)

    try:
        from songshare_analysis.id3_io import read_id3

        new_info = read_id3(target_path)
        new_tags = new_info.get("tags", {}) or {}
    except Exception:
        new_tags = {}

    _print_apply_result(
        target_path, delta, before_tags, new_tags, proposed, result["applied"]
    )

    return result
