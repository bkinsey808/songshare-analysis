from __future__ import annotations

from typing import Any


def _print_basic_info(
    info: dict[str, Any], logger: Any, verbose: bool = False
) -> dict[str, Any]:
    """Log basic file metadata and tags at INFO when `verbose` is True.

    Returns the tags dict.
    """

    if not verbose:
        return info.get("tags", {}) or {}

    logger.info("File: %s", info.get("path"))
    if info.get("info"):
        inf = info["info"]
        logger.info("Metadata:")
        for k, v in inf.items():
            if v is not None:
                s = str(v)
                if len(s) > 200:
                    s = s[:197] + "..."
                logger.info("  %s: %s", k, s)

    tags = info.get("tags", {}) or {}
    if tags:
        logger.info("Tags:")
        for k, v in sorted(tags.items()):
            # Avoid logging raw binary data or extremely long values
            if isinstance(v, (bytes, bytearray)):
                logger.info("  %s: <binary data %d bytes>", k, len(v))
                continue
            s = str(v)
            if len(s) > 200:
                s = s[:197] + "..."
            logger.info("  %s: %s", k, s)
    else:
        logger.info("No tags found.")

    return tags


def _fetch_and_print_musicbrainz(
    tags: dict[str, Any], logger: Any, verbose: bool = False
) -> dict[str, Any] | None:
    """Fetch metadata from MusicBrainz and print results.

    Returns mb_info or None on error.
    """
    from .id3_mb import musicbrainz_lookup

    try:
        mb_info = musicbrainz_lookup(tags)
        if not verbose:
            return mb_info

        if mb_info:
            logger.info("MusicBrainz:")
            for k, v in mb_info.items():
                # Avoid logging binary data (cover art) or extremely long fields
                if isinstance(v, (bytes, bytearray)):
                    logger.info("  %s: <binary data %d bytes>", k, len(v))
                    continue
                s = str(v)
                if len(s) > 200:
                    s = s[:197] + "..."
                logger.info("  %s: %s", k, s)
        else:
            logger.info("MusicBrainz: no matches found")

        return mb_info
    except Exception as exc:  # pragma: no cover - network/runtime
        logger.error("MusicBrainz lookup failed: %s", exc)
        return None


def _should_skip_mb_fetch(tags: dict[str, Any]) -> bool:
    """Return True if we can skip MusicBrainz fetch because tags/IDs are present.

    We consider the core tags to be TIT2 (title), TPE1 (artist), and TALB (album).
    If all core tags are present or either musicbrainz_recording_id or
    musicbrainz_release_id TXXX frames are present, we can skip the lookup.
    """
    if not tags:
        return False
    core = ("TIT2", "TPE1", "TALB")
    if all(tags.get(k) for k in core):
        return True
    # Check MusicBrainz ID TXXX frames
    if tags.get("TXXX:musicbrainz_recording_id") or tags.get(
        "TXXX:musicbrainz_release_id"
    ):
        return True
    return False


def _print_proposed_metadata(proposed: dict[str, Any]) -> None:
    """Print proposed metadata in a consistent, truncated format.

    `proposed` is a mapping of tag keys to values; long values are truncated
    for readability and binary values are replaced with a placeholder.
    """

    print("\nProposed metadata:")
    for k, v in proposed.items():
        if isinstance(v, (bytes, bytearray)):
            print(f"  {k}: <binary data {len(v)} bytes>")
            continue
        s = str(v)
        if len(s) > 200:
            s = s[:197] + "..."
        print(f"  {k}: {s}")
