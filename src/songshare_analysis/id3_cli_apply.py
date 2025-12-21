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
    target_path: Path,
    args: Any,
    logger: Any,
    mb_info: dict[str, Any],
    existing_tags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Propose metadata derived from MusicBrainz info and optionally apply it to a path.

    Only print a preview if the proposed metadata would actually add or change
    values compared to `existing_tags`.

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

    # Determine whether embedding will be attempted and whether it would change
    # the file (no-op when art already embedded). Try a download first so we can
    # suppress a cover-embed proposal if the image cannot be fetched.
    cover_url = mb_info.get("cover_art")
    embed_requested = bool(getattr(args, "embed_cover_art", False))
    embed_would_write = False
    cover_bytes: bytes | None = None
    if embed_requested and cover_url:
        existing = existing_tags or {}
        # If any existing tag looks like embedded binary/art, consider it present
        if any(k.startswith("APIC") for k in existing.keys()) or any(
            isinstance(v, (bytes, bytearray)) for v in existing.values()
        ):
            embed_would_write = False
        else:
            # Try to download the image so that we only show a proposal if the
            # download is likely to succeed. If download fails, don't show embed
            # proposal.
            try:
                from .id3_cover import _download_cover_art

                # Attempt a short download; allow test to monkeypatch this
                cover_bytes = _download_cover_art(str(cover_url), timeout=5)
                embed_would_write = True
            except Exception:
                # Download failed; do not propose an embed
                embed_would_write = False
                cover_bytes = None

    # If there's no proposed metadata AND no embed to perform, nothing to do.
    if not proposed and not embed_would_write:
        logger.info("No proposed metadata to apply")
        return result

    # Compute the delta between proposed metadata and what's already present
    # We want to show only keys that would actually result in a write.
    delta: dict[str, object] = {}
    existing = existing_tags or {}

    for k, v in proposed.items():
        # TXXX keys are written directly; if identical value already present, no write.
        if k.startswith("TXXX:"):
            existing_val = existing.get(k)
            if existing_val is None or str(existing_val).strip() != str(v).strip():
                delta[k] = v
            continue

        # For core frames (TIT2/TPE1/TALB): if empty, we'll write the core frame.
        existing_core = existing.get(k)
        if not existing_core:
            delta[k] = v
            continue

        # If the existing core value already matches the proposed value, no write
        # will be necessary (and we should not create a TXXX proposed frame).
        if str(existing_core).strip() == str(v).strip():
            continue

        # Core exists but differs; apply will add/update a
        # TXXX:musicbrainz_proposed_<FRAME>
        proposed_key = "TXXX:musicbrainz_proposed_" + k
        existing_proposed = existing.get(proposed_key)
        if (
            existing_proposed is None
            or str(existing_proposed).strip() != str(v).strip()
        ):
            # The actual write will be to the TXXX proposed key; show that instead
            delta[proposed_key] = v

    # If there are no metadata changes and no embed to write, nothing to do.
    if not delta and not embed_would_write:
        logger.info("No proposed metadata to apply")
        return result

    # Print proposals (may be empty dict if only cover will be embedded)
    _print_proposed_metadata(delta)

    # If embedding will be performed, show that explicitly in the preview
    if embed_would_write:
        if isinstance(cover_url, (bytes, bytearray)):
            print(f"  Will embed cover art: <binary data {len(cover_url)} bytes>")
        else:
            s = str(cover_url)
            if len(s) > 200:
                s = s[:197] + "..."
            print(f"  Will embed cover art: {s}")

    if not _confirm_apply(args):
        print("Aborted; no changes made.")
        return result

    # Attempt embed (if requested); if embedding fails we skip apply
    if embed_requested:
        if cover_bytes is not None:
            try:
                from .id3_cover import _embed_cover_mp3

                _embed_cover_mp3(target_path, cover_bytes)
                logger.info("Cover art embedded for %s", target_path)
                result["embed"] = True
            except Exception:
                logger.warning(
                    "Cover art embedding failed; skipping metadata apply for this file."
                )
                result["embed"] = False
                return result
        else:
            embed_result = _maybe_embed_cover(target_path, args, mb_info, logger)
            result["embed"] = embed_result
            if embed_result is False:
                return result
    else:
        result["embed"] = None

    # Only perform a metadata apply if there are actual metadata changes to make
    if not delta:
        # No metadata writes necessary (embed may have succeeded)
        return result

    applied_ok = _apply_metadata_safe(target_path, proposed, logger)
    result["applied"] = bool(applied_ok)
    return result
