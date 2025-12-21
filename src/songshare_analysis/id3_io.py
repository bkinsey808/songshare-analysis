"""IO and tag write/read helpers factored out from `id3.py`.

Contains: read_id3, _read_id3_only, apply_metadata, backups, and write helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from mutagen import File as MutagenFile  # type: ignore
else:
    try:
        from mutagen import File as MutagenFile  # type: ignore[import]
    except Exception:  # pragma: no cover - runtime dependency
        MutagenFile = None  # type: ignore[assignment]


def read_id3(path: Path) -> Dict[str, Any]:
    """Read tags and basic metadata from ``path`` using Mutagen.

    Returns a dict with keys ``path``, ``tags`` (mapping of frame key -> str),
    and ``info`` (length/bitrate/sample_rate when available).
    """
    if MutagenFile is None:
        raise RuntimeError(
            "mutagen is required to read ID3 tags. Install with `pip install mutagen`"
        )

    result: Dict[str, Any] = {"path": str(path), "tags": {}, "info": {}}

    try:
        audio = MutagenFile(str(path))
    except Exception:
        audio = None

    if audio is None:
        return _read_id3_only(path)

    if getattr(audio, "tags", None):
        for k, v in audio.tags.items():
            try:
                result["tags"][str(k)] = str(v)
            except Exception:
                result["tags"][str(k)] = repr(v)

    info: Dict[str, Any] = {}
    if getattr(audio, "info", None):
        info["length"] = getattr(audio.info, "length", None)
        info["bitrate"] = getattr(audio.info, "bitrate", None)
        info["sample_rate"] = getattr(audio.info, "sample_rate", None)
    result["info"] = info

    return result


def _read_id3_only(path: Path) -> Dict[str, Any]:
    import importlib

    result: Dict[str, Any] = {"path": str(path), "tags": {}, "info": {}}

    try:
        id3_mod = importlib.import_module("mutagen.id3")
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("mutagen.id3 is required to read ID3-only files") from exc

    ID3_ctor: Any = id3_mod.ID3
    id3 = ID3_ctor(str(path))

    for k, v in id3.items():
        try:
            result["tags"][str(k)] = str(v)
        except Exception:
            result["tags"][str(k)] = repr(v)

    result["info"] = {}
    return result


# --- Writing & apply helpers ---


def apply_metadata(
    path: Path,
    proposed: Dict[str, str],
    make_backup: bool = True,
) -> None:
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
    import json

    bak = path.with_suffix(path.suffix + ".tags.bak.json")
    try:
        orig = read_id3(path)
    except Exception:
        orig = {"path": str(path), "tags": {}, "info": {}}

    try:
        with open(bak, "w", encoding="utf8") as f:
            json.dump(orig, f, indent=2)
    except Exception:
        pass


def _write_mp3_tags(path: Path, proposed: Dict[str, str]) -> None:
    try:
        from mutagen.id3 import ID3
        from mutagen.id3._frames import TALB, TCON, TIT2, TPE1, TXXX
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("mutagen.id3 required to write tags") from exc

    ID3_ctor: Any = ID3
    TIT2_ctor: Any = TIT2
    TPE1_ctor: Any = TPE1
    TALB_ctor: Any = TALB
    TCON_ctor: Any = TCON
    TXXX_ctor: Any = TXXX

    try:
        tags = ID3_ctor(str(path))
    except Exception:
        tags = ID3_ctor()

    _add_common_mp3_frames(tags, proposed, TIT2_ctor, TPE1_ctor, TALB_ctor, TCON_ctor)
    _add_txxx_frames(tags, proposed, TXXX_ctor)
    _save_tags_with_fallback(tags, path)


def _add_common_mp3_frames(
    tags: Any,
    proposed: Dict[str, str],
    TIT2_ctor: Any,
    TPE1_ctor: Any,
    TALB_ctor: Any,
    TCON_ctor: Any,
) -> None:
    def _has_value(frame_key: str) -> bool:
        try:
            existing = tags.get(frame_key)
            return bool(existing) and bool(str(existing).strip())
        except Exception:
            return False

    def _maybe_add_or_propose(frame_key: str, ctor: Any) -> None:
        if not proposed.get(frame_key):
            return
        if _has_value(frame_key):
            # If the existing core frame matches the proposed value exactly,
            # there is nothing to do (no need to create a TXXX proposed frame).
            try:
                existing = str(tags.get(frame_key))
            except Exception:
                existing = ""
            if str(existing).strip() == str(proposed[frame_key]).strip():
                return
            proposed["TXXX:musicbrainz_proposed_" + frame_key] = proposed[frame_key]
            return
        ctor_args = {"encoding": 3, "text": [proposed[frame_key]]}
        tags.add(ctor(**ctor_args))

    _maybe_add_or_propose("TIT2", TIT2_ctor)
    _maybe_add_or_propose("TPE1", TPE1_ctor)
    _maybe_add_or_propose("TALB", TALB_ctor)
    _maybe_add_or_propose("TCON", TCON_ctor)


def _add_txxx_frames(tags: Any, proposed: Dict[str, str], TXXX_ctor: Any) -> None:
    for k, v in proposed.items():
        if k.startswith("TXXX:"):
            desc = k.split("TXXX:", 1)[1]
            tags.add(TXXX_ctor(encoding=3, desc=desc, text=[v]))


def _save_tags_with_fallback(tags: Any, path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size == 0:
            with open(str(path), "wb") as f:
                f.write(b"\x00" * 128)
        tags.save(str(path))
    except Exception:
        try:
            with open(str(path), "r+b") as f:
                tags.save(f)
        except Exception as exc:  # pragma: no cover - runtime
            raise RuntimeError("Failed to write ID3 tags") from exc


def _write_generic_tags(path: Path, proposed: Dict[str, str]) -> None:
    audio = MutagenFile(str(path))
    if audio is None:
        raise RuntimeError("Unsupported file format for writing tags")

    if getattr(audio, "tags", None) is None:
        audio.add_tags()

    def _maybe_set_or_propose(key: str) -> None:
        if not proposed.get(key):
            return
        try:
            existing = audio.tags.get(key)
        except Exception:
            existing = None
        if existing and bool(str(existing).strip()):
            audio.tags["TXXX:musicbrainz_proposed_" + key] = proposed[key]
        else:
            audio.tags[key] = proposed[key]

    _maybe_set_or_propose("TIT2")
    _maybe_set_or_propose("TPE1")
    _maybe_set_or_propose("TALB")

    for k, v in proposed.items():
        if k.startswith("TXXX:"):
            if not audio.tags.get(k):
                audio.tags[k] = v

    audio.save()
