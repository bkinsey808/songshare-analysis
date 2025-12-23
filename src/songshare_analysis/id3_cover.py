"""Cover art helpers factored out of `id3.py`.

Contains downloading and embedding logic. Export `_download_cover_art`,
`_embed_cover_mp3`, and `_embed_cover_if_needed`.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from mutagen.id3 import ID3
    from mutagen.id3._frames import APIC

    # Use the shared `ID3Like` Protocol from `types.py` so tests and other
    # modules can import the structural type without causing runtime
    # import cycles.
    from .types import ID3Like

logger = logging.getLogger(__name__)

# Public exports for other modules (and to satisfy static analyzers)
__all__ = [
    "_download_cover_art",
    "_embed_cover_if_needed",
    "_embed_cover_mp3",
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
                msg = "Downloaded cover art is not bytes"
                raise TypeError(msg)
            return bytes(data)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            if attempt < retries:
                with contextlib.suppress(Exception):
                    import time

                    time.sleep(0.5 * attempt)
            continue
    msg = "Failed to download cover art"
    raise RuntimeError(msg) from last_err


def _embed_cover_mp3(path: Path, image_bytes: bytes, mime: str = "image/jpeg") -> None:
    try:
        from mutagen.id3 import ID3  # noqa: PLC0415
        from mutagen.id3._frames import APIC  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - runtime dependency
        msg = "mutagen.id3 required to embed cover art"
        raise RuntimeError(msg) from exc

    id3_ctor: type[ID3] = ID3
    tags: ID3Like
    try:
        # Cast the untyped object returned by Mutagen to `ID3Like` so the
        # static type checker understands we rely only on the small set of
        # methods declared on that Protocol below.
        tags = cast("ID3Like", id3_ctor(str(path)))
    except Exception:  # noqa: BLE001
        tags = cast("ID3Like", id3_ctor())

    if tags.getall("APIC"):
        return

    apic_ctor: type[APIC] = APIC

    apic = apic_ctor(
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
        from mutagen.id3 import ID3  # noqa: PLC0415

        id3_ctor: type[ID3] = ID3
        tags: ID3Like
        try:
            tags = cast("ID3Like", id3_ctor(str(path)))
        except Exception:  # noqa: BLE001
            tags = cast("ID3Like", id3_ctor())
        if tags.getall("APIC"):
            logger.info("File %s already has cover art; skipping embed", path)
            return None
    except Exception:  # noqa: BLE001
        # If mutagen isn't available or fails, proceed and let later steps handle errors
        pass

    try:
        image_bytes = _download_cover_art(url, timeout=timeout)
        # backup handled by caller if desired
        _embed_cover_mp3(path, image_bytes)
        logger.info("Embedded cover art into %s", path)
        return True
    except Exception:  # pragma: no cover - network/runtime
        # Suppress cover art embedding failure messages
        return False
