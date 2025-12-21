from __future__ import annotations

from pathlib import Path
from typing import Any

from .id3_cli_print import _print_proposed_metadata
from .id3_io import apply_metadata
from .id3_mb import propose_metadata_from_mb


def _confirm_apply(args: Any) -> bool:
    """Return True if the operation should proceed (handles -y/--yes).

    Returns True immediately when `args.yes` is truthy; otherwise prompts the
    user with a yes/no question and returns True only on an explicit yes.
    """

    if getattr(args, "yes", False):
        return True
    ans = input("Apply these changes? [y/N] ")
    return ans.strip().lower() in ("y", "yes")


def _maybe_embed_cover(
    target_path: Path, args: Any, mb_info: dict[str, Any], logger: Any
) -> bool | None:
    """Try embedding cover art if requested. Returns True/None/False as docs describe.

    - True: embedded successfully
    - None: skipped (non-MP3 or already present or no URL)
    - False: embedding failed (caller should abort apply)
    """

    if not getattr(args, "embed_cover_art", False):
        return None

    cover_url = mb_info.get("cover_art")
    if not isinstance(cover_url, str):
        return None

    # Import dynamically to avoid circular imports at module import time
    from .id3_cover import _embed_cover_if_needed

    try:
        res = _embed_cover_if_needed(target_path, cover_url)
        if res is True:
            logger.info("Cover art embedded for %s", target_path)
        elif res is False:
            # Visible warning when embedding explicitly failed
            logger.warning(
                "Cover art embedding failed; skipping metadata apply for this file."
            )
        return res
    except Exception:  # pragma: no cover - runtime/network
        logger.warning(
            "Cover art embedding failed; skipping metadata apply for this file."
        )
        return False


def _apply_metadata_safe(
    target_path: Path, proposed: dict[str, Any], logger: Any
) -> bool:
    """Apply metadata and log any unexpected exceptions.

    Returns True on successful apply, False on failure. On success this logs a
    short confirmation at INFO; on failure it logs an error and returns False.
    """

    try:
        apply_metadata(target_path, proposed)
        logger.info("Metadata applied (backup created).")
        return True
    except Exception as exc:  # pragma: no cover - runtime
        logger.error("Failed to apply metadata: %s", exc)
        return False


def _maybe_propose_and_apply(
    target_path: Path, args: Any, logger: Any, mb_info: dict[str, Any]
) -> dict[str, Any]:
    """Propose metadata derived from MusicBrainz info and optionally apply it to a path.

    Returns a dict describing what happened with keys:
      - applied: bool (True if metadata was applied)
      - embed: True|False|None (embed outcome)
    """
    result = {"applied": False, "embed": None}

    apply_flag = getattr(args, "apply_metadata", False) or getattr(
        args, "apply-metadata", False
    )
    if not apply_flag:
        return result

    proposed = propose_metadata_from_mb(mb_info)
    if not proposed:
        logger.info("No proposed metadata to apply")
        return result

    _print_proposed_metadata(proposed)

    if not _confirm_apply(args):
        print("Aborted; no changes made.")
        return result

    embed_result = _maybe_embed_cover(target_path, args, mb_info, logger)
    result["embed"] = embed_result
    if embed_result is False:
        return result

    applied_ok = _apply_metadata_safe(target_path, proposed, logger)
    result["applied"] = bool(applied_ok)
    return result
