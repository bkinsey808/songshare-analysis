"""Cover art helpers factored out of `id3.py`.

Contains downloading and embedding logic. Export `_download_cover_art`,
`_embed_cover_mp3`, and `_embed_cover_if_needed`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Public exports for other modules (and to satisfy static analyzers)
__all__ = [
    "_download_cover_art",
    "_embed_cover_mp3",
    "_embed_cover_if_needed",
]


def _download_cover_art(url: str, timeout: int = 5, retries: int = 2) -> bytes:
    import urllib.error
    import urllib.request

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = resp.read()
            if not isinstance(data, (bytes, bytearray)):
                raise RuntimeError("Downloaded cover art is not bytes")
            return bytes(data)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            if attempt < retries:
                try:
                    import time

                    time.sleep(0.5 * attempt)
                except Exception:
                    pass
            continue
    raise RuntimeError("Failed to download cover art") from last_err


def _embed_cover_mp3(path: Path, image_bytes: bytes, mime: str = "image/jpeg") -> None:
    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import APIC
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("mutagen.id3 required to embed cover art") from exc

    ID3_ctor: Any = ID3
    try:
        tags: Any = ID3_ctor(str(path))
    except Exception:
        tags = ID3_ctor()

    if tags.getall("APIC"):
        return

    APIC_ctor: Any = APIC

    apic = APIC_ctor(
        encoding=3,  # 3 = UTF-8
        mime=mime,
        type=3,  # 3 = cover(front)
        desc="Cover",
        data=image_bytes,
    )
    tags.add(apic)
    tags.save(str(path))


def _embed_cover_if_needed(path: Path, url: str, timeout: int = 5) -> bool | None:
    """Download and embed cover art into `path` if it doesn't already have art.

    Returns:
      - True on successful embed
      - False on failure (network/IO errors)
      - None when embedding is skipped (non-MP3 or already has art)
    """
    # Quick check: for MP3 only
    if path.suffix.lower() != ".mp3":
        logger.debug("Skipping cover art embed for non-MP3: %s", path)
        return None

    # If the file already has APIC frames, skip without downloading
    try:
        from mutagen.id3 import ID3

        ID3_ctor: Any = ID3
        try:
            tags: Any = ID3_ctor(str(path))
        except Exception:
            tags = ID3_ctor()
        if tags.getall("APIC"):
            logger.info("File %s already has cover art; skipping embed", path)
            return None
    except Exception:
        # If mutagen isn't available or fails, proceed and let later steps handle errors
        pass

    try:
        image_bytes = _download_cover_art(url, timeout=timeout)
        # backup handled by caller if desired
        _embed_cover_mp3(path, image_bytes)
        logger.info("Embedded cover art into %s", path)
        return True
    except Exception as exc:  # pragma: no cover - network/runtime
        logger.error("Cover art embedding failed for %s: %s", path, exc)
        return False
