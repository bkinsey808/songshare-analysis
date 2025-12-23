"""IO and tag write/read helpers factored out from `id3.py`.

Contains: read_id3, _read_id3_only, apply_metadata, backups, and write helpers.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    # Keep type-only imports grouped and sorted for readability
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3
    from mutagen.id3._frames import TALB, TCON, TIT2, TPE1, TXXX

    # Import shared types used for typing across modules
    from .types import ID3Like, ID3ReadResult
else:
    try:
        from mutagen import File as MutagenFile
    except ImportError:  # pragma: no cover - runtime dependency
        MutagenFile = None


# `ID3ReadResult` is defined in `songshare_analysis.types` and imported
# under TYPE_CHECKING above. See `types.py` for the authoritative shape.

if TYPE_CHECKING:
    from mutagen import File as MutagenFile
else:
    try:
        from mutagen import File as MutagenFile
    except ImportError:  # pragma: no cover - runtime dependency
        MutagenFile = None


def read_id3(path: Path) -> ID3ReadResult:
    """Read tags and basic metadata from ``path`` using Mutagen.

    Returns an :class:`ID3ReadResult` TypedDict with keys ``path``, ``tags``,
    and ``info``.
    """
    if MutagenFile is None:
        msg = (
            "mutagen is required to read ID3 tags. "
            "Install with `pip install mutagen`"
        )
        raise RuntimeError(msg)

    result: ID3ReadResult = {"path": str(path), "tags": {}, "info": {}}

    try:
        audio = MutagenFile(str(path))
    except Exception:  # noqa: BLE001
        audio = None

    if audio is None:
        return _read_id3_only(path)

    if getattr(audio, "tags", None):
        for k, v in audio.tags.items():
            try:
                result["tags"][str(k)] = str(v)
            except Exception:
                result["tags"][str(k)] = repr(v)

    info: dict[str, Any] = {}
    if getattr(audio, "info", None):
        info["length"] = getattr(audio.info, "length", None)
        info["bitrate"] = getattr(audio.info, "bitrate", None)
        info["sample_rate"] = getattr(audio.info, "sample_rate", None)
    result["info"] = info

    return result


def _read_id3_only(path: Path) -> ID3ReadResult:
    import importlib  # noqa: PLC0415 (dynamic import to avoid runtime dependency at module import time)

    result: ID3ReadResult = {"path": str(path), "tags": {}, "info": {}}

    try:
        id3_mod = importlib.import_module("mutagen.id3")
    except ImportError as exc:  # pragma: no cover - runtime dependency
        msg = "mutagen.id3 is required to read ID3-only files"
        raise RuntimeError(msg) from exc

    id3_ctor: type[ID3] = id3_mod.ID3
    # Mutagen's constructor returns an untyped object; cast it to the
    # Protocol close to the boundary where the untyped value enters our
    # codebase so the rest of the function can rely on the documented
    # `ID3Like` interface and avoid `Any` sprinkled everywhere.
    id3 = cast("ID3Like", id3_ctor(str(path)))

    for k, v in id3.items():
        try:
            result["tags"][str(k)] = str(v)
        except Exception:  # noqa: BLE001
            result["tags"][str(k)] = repr(v)

    result["info"] = {}
    return result


# --- Writing & apply helpers ---


def apply_metadata(
    path: Path,
    proposed: dict[str, str],
    *,
    make_backup: bool = True,
) -> None:
    """Apply proposed metadata to the file at ``path``.

    Optionally creates a backup when ``make_backup`` is True.
    """
    if not proposed:
        return

    if make_backup:
        _backup_tags(path)

    suffix = path.suffix.lower()
    if suffix == ".mp3":
        _write_mp3_tags(path, proposed)
    else:
        _write_generic_tags(path, proposed)


def _backup_tags(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".tags.bak.json")
    try:
        orig = read_id3(path)
    except Exception:  # noqa: BLE001
        orig = {"path": str(path), "tags": {}, "info": {}}

    with contextlib.suppress(Exception), bak.open("w", encoding="utf8") as f:
        json.dump(orig, f, indent=2)


def _write_mp3_tags(path: Path, proposed: dict[str, str]) -> None:
    try:
        from mutagen.id3 import ID3  # noqa: PLC0415
        from mutagen.id3._frames import TALB, TCON, TIT2, TPE1, TXXX  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - runtime dependency
        msg = "mutagen.id3 required to write tags"
        raise RuntimeError(msg) from exc

    id3_ctor: type[ID3] = ID3
    tit2_ctor: type[TIT2] = TIT2
    tpe1_ctor: type[TPE1] = TPE1
    talb_ctor: type[TALB] = TALB
    tcon_ctor: type[TCON] = TCON
    txxx_ctor: type[TXXX] = TXXX

    try:
        # Cast the untyped runtime object to ID3Like for better static
        # checking in downstream helpers (e.g. _add_common_mp3_frames).
        tags = cast("ID3Like", id3_ctor(str(path)))
    except Exception:  # noqa: BLE001
        tags = cast("ID3Like", id3_ctor())

    _add_common_mp3_frames(tags, proposed, tit2_ctor, tpe1_ctor, talb_ctor, tcon_ctor)
    _add_txxx_frames(tags, proposed, txxx_ctor)
    _save_tags_with_fallback(tags, path)


def _add_common_mp3_frames(
    tags: ID3Like,
    proposed: dict[str, str],
    tit2_ctor: type[TIT2],
    tpe1_ctor: type[TPE1],
    talb_ctor: type[TALB],
    tcon_ctor: type[TCON],
) -> None:  # noqa: PLR0913 (function intentionally accepts multiple ctor types)
    def _has_value(frame_key: str) -> bool:
        try:
            existing = tags.get(frame_key)
            return bool(existing) and bool(str(existing).strip())
        except Exception:  # noqa: BLE001
            return False

    def _maybe_add_or_propose(frame_key: str, ctor: type[object]) -> None:
        if not proposed.get(frame_key):
            return
        if _has_value(frame_key):
            # If the existing core frame matches the proposed value exactly,
            # there is nothing to do (no need to create a TXXX proposed frame).
            try:
                existing = str(tags.get(frame_key))
            except Exception:  # noqa: BLE001
                existing = ""
            if str(existing).strip() == str(proposed[frame_key]).strip():
                return
            proposed["TXXX:musicbrainz_proposed_" + frame_key] = proposed[frame_key]
            return
        ctor_args = {"encoding": 3, "text": [proposed[frame_key]]}
        tags.add(ctor(**ctor_args))

    _maybe_add_or_propose("TIT2", tit2_ctor)
    _maybe_add_or_propose("TPE1", tpe1_ctor)
    _maybe_add_or_propose("TALB", talb_ctor)
    _maybe_add_or_propose("TCON", tcon_ctor)


def _add_txxx_frames(
    tags: ID3Like,
    proposed: dict[str, str],
    txxx_ctor: type[TXXX],
) -> None:
    for k, v in proposed.items():
        if k.startswith("TXXX:"):
            desc = k.split("TXXX:", 1)[1]
            tags.add(txxx_ctor(encoding=3, desc=desc, text=[v]))


def _save_tags_with_fallback(tags: ID3Like, path: Path) -> None:
    """Save tags reliably and attempt to flush to disk so writes are visible
    on unusual filesystems (WSL/NTFS mounts, network filesystems, etc).

    We prefer in-place writes using Mutagen's API, but explicitly fsync the
    file descriptor after writing and perform a best-effort os.sync() to
    reduce the chance of silent write failures on WSL. If both primary and
    fallback methods fail we raise a clear RuntimeError.
    """
    # Mutagen can save either by path or by file-object. Try the simple path
    # save first, then ensure the data is flushed to disk with fsync/os.sync.
    try:
        if path.exists() and path.stat().st_size == 0:
            with path.open("wb") as f:
                f.write(b"\x00" * 128)
        tags.save(str(path))

        # Best-effort: open and fsync to ensure data hits the device.
        try:
            with path.open("r+b") as f:
                f.flush()
                os.fsync(f.fileno())
            try:
                # Global sync may help on some kernel/filesystem combinations
                os.sync()
            except Exception:
                # Ignore os.sync failures; fsync above is the more important step.
                pass
        except Exception:
            # If we can't open/fsync the file, continue to fallback behaviour.
            pass

        return
    except Exception:  # noqa: BLE001
        # Fallback to writing via an open file object (in-place).
        try:
            with path.open("r+b") as f:
                tags.save(f)
                try:
                    f.flush()
                    os.fsync(f.fileno())
                    try:
                        os.sync()
                    except Exception:
                        pass
                except Exception:
                    # If fsync fails here, fall through to the outer exception.
                    pass
            return
        except Exception as exc:  # pragma: no cover - runtime
            msg = "Failed to write ID3 tags"
            raise RuntimeError(msg) from exc


def _write_generic_tags(path: Path, proposed: dict[str, str]) -> None:
    audio = MutagenFile(str(path))
    if audio is None:
        msg = "Unsupported file format for writing tags"
        raise RuntimeError(msg)

    if getattr(audio, "tags", None) is None:
        audio.add_tags()

    def _maybe_set_or_propose(key: str) -> None:
        if not proposed.get(key):
            return
        try:
            existing = audio.tags.get(key)
        except Exception:  # noqa: BLE001
            existing = None
        if existing and bool(str(existing).strip()):
            audio.tags["TXXX:musicbrainz_proposed_" + key] = proposed[key]
        else:
            audio.tags[key] = proposed[key]

    _maybe_set_or_propose("TIT2")
    _maybe_set_or_propose("TPE1")
    _maybe_set_or_propose("TALB")

    for k, v in proposed.items():
        if k.startswith("TXXX:") and not audio.tags.get(k):
            audio.tags[k] = v

    audio.save()
