from __future__ import annotations

from collections.abc import Mapping
from logging import Logger
from pathlib import Path
from typing import Any

from songshare_analysis.types import Args, ErrorLoggerLike, LoggerLike, MBInfo, TagValue


def _confirm_apply(args: Args) -> bool:
    if getattr(args, "yes", False):
        return True
    ans = input("Apply these changes? [y/N] ")
    return ans.strip().lower() in ("y", "yes")


def _maybe_embed_cover(
    target_path: Path,
    args: Args,
    mb_info: MBInfo | Mapping[str, Any],
    logger: Logger | LoggerLike | None,
) -> bool | None:
    if not getattr(args, "embed_cover_art", False):
        return None

    cover_url = mb_info.get("cover_art")
    if not isinstance(cover_url, str):
        return None

    from songshare_analysis.id3_cover import _embed_cover_if_needed

    try:
        res = _embed_cover_if_needed(target_path, cover_url)
        if res is True and logger:
            logger.info("Cover art embedded for %s", target_path)
        if res is False and logger:
            msg = (
                "Cover art embedding failed; " "skipping metadata apply for this file."
            )
            logger.warning(msg)
        return res
    except Exception:  # pragma: no cover - runtime/network
        if logger:
            msg = (
                "Cover art embedding failed; " "skipping metadata apply for this file."
            )
            logger.warning(msg)
        return False


def _apply_metadata_safe(
    target_path: Path, proposed: dict[str, str], logger: Logger | ErrorLoggerLike
) -> bool:
    try:
        # Resolve via the public module so tests can monkeypatch the attribute
        from . import id3_cli_apply as _id3_apply

        _id3_apply.apply_metadata(target_path, proposed)
        if isinstance(logger, Logger):
            logger.info("Metadata applied (backup created).")
        return True
    except Exception as exc:  # pragma: no cover - runtime
        logger.error("Failed to apply metadata: %s", exc)
        return False


def _prepare_embed(
    args: Args,
    mb_info: MBInfo | Mapping[str, Any],
    existing_tags: Mapping[str, TagValue] | None = None,
) -> tuple[str | None, bool, bool, bytes | None]:
    cover_url = mb_info.get("cover_art")
    if not isinstance(cover_url, str):
        cover_url = None
    embed_requested = bool(getattr(args, "embed_cover_art", False))
    embed_would_write = False
    cover_bytes: bytes | None = None

    if not (embed_requested and cover_url):
        return cover_url, embed_requested, embed_would_write, cover_bytes

    existing = existing_tags or {}
    if any(k.startswith("APIC") for k in existing.keys()) or any(
        isinstance(v, (bytes, bytearray)) for v in existing.values()
    ):
        return cover_url, embed_requested, False, None

    try:
        from songshare_analysis.id3_cover import _download_cover_art

        cover_bytes = _download_cover_art(str(cover_url), timeout=5)
        embed_would_write = True
    except Exception:
        cover_bytes = None
        embed_would_write = False

    return cover_url, embed_requested, embed_would_write, cover_bytes


def _compute_delta(
    proposed: dict[str, str], existing_tags: Mapping[str, TagValue] | None = None
) -> dict[str, TagValue]:
    delta: dict[str, TagValue] = {}
    existing = existing_tags or {}

    for k, v in proposed.items():
        if k.startswith("TXXX:"):
            existing_val = existing.get(k)
            if existing_val is None or str(existing_val).strip() != str(v).strip():
                delta[k] = v
            continue

        existing_core = existing.get(k)
        if not existing_core:
            delta[k] = v
            continue

        if str(existing_core).strip() == str(v).strip():
            continue

        proposed_key = "TXXX:musicbrainz_proposed_" + k
        existing_proposed = existing.get(proposed_key)
        if (
            existing_proposed is None
            or str(existing_proposed).strip() != str(v).strip()
        ):
            delta[proposed_key] = v

    return delta


def _print_embed_preview(cover_url: str | bytes | None) -> None:
    if isinstance(cover_url, (bytes, bytearray)):
        print(f"  Will embed cover art: <binary data {len(cover_url)} bytes>)")
        return

    s = str(cover_url)
    if len(s) > 200:
        s = s[:197] + "..."
    print(f"  Will embed cover art: {s}")


def _perform_embed(
    target_path: Path,
    args: Args,
    logger: Logger | LoggerLike | None,
    mb_info: MBInfo | Mapping[str, Any],
    cover_bytes: bytes | None,
    _cover_url: str | bytes | None,
) -> bool | None:
    if not bool(getattr(args, "embed_cover_art", False)):
        return None

    if cover_bytes is not None:
        try:
            from songshare_analysis.id3_cover import _embed_cover_mp3

            _embed_cover_mp3(target_path, cover_bytes)
            if logger:
                logger.info("Cover art embedded for %s", target_path)
            return True
        except Exception:  # pragma: no cover - runtime/network
            if logger:
                msg = (
                    "Cover art embedding failed; "
                    "skipping metadata apply for this file."
                )
                logger.warning(msg)
            return False

    return _maybe_embed_cover(target_path, args, mb_info, logger)


def _verify_apply_result(
    target_path: Path, proposed: dict[str, str], logger: Logger | LoggerLike
) -> bool:
    try:
        from songshare_analysis.id3_io import read_id3

        new_info = read_id3(target_path)
        new_tags = new_info.get("tags", {}) or {}
    except Exception:  # pragma: no cover - defensive/read failure
        if logger:
            logger.warning(
                "Re-read failed; write may not have succeeded for %s", target_path
            )
        return False

    remaining = _compute_delta(proposed, new_tags)
    if remaining:
        if logger:
            logger.warning(
                "Apply reported success but tags unchanged for %s",
                target_path,
            )
        return False

    return True


def _fmt_tag_value(val: object) -> str:
    try:
        if isinstance(val, (bytes, bytearray)):
            return val.decode("utf8", errors="backslashreplace")
        return str(val)
    except Exception:
        return repr(val)


def _print_apply_result(
    target_path: Path,
    delta: Mapping[str, object],
    before_tags: Mapping[str, object],
    new_tags: Mapping[str, object],
    proposed: dict[str, str],
    applied: bool | None,
) -> None:
    if applied:
        print(f"Applied metadata to {target_path}:")
        for k in sorted(delta.keys()):
            old = before_tags.get(k)
            new = new_tags.get(k)
            if new is None:
                new = proposed.get(k)
            old_s = _fmt_tag_value(old) if old is not None else "(was absent)"
            new_s = _fmt_tag_value(new)
            print(f"  {k}: {old_s} -> {new_s}")
    else:
        print(f"No changes applied to {target_path}")
