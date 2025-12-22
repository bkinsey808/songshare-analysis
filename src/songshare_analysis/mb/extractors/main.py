from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .populators import (
    _populate_artist_meta,
    _populate_basic_fields,
    _populate_genres,
    _populate_recording_fields,
    _populate_release_fields,
    _populate_urls,
)

if TYPE_CHECKING:
    from songshare_analysis.types import MBInfo


def _mb_extract_fields(
    rec: Mapping[str, object],
    candidate: Mapping[str, object],
) -> MBInfo:
    out: MBInfo = {"provenance": {"source": "musicbrainz"}}

    _populate_basic_fields(out, rec, candidate)
    _populate_recording_fields(out, rec, candidate)
    _populate_release_fields(out, rec)
    _populate_genres(out, rec)
    _populate_urls(out, rec)
    _populate_artist_meta(out, rec)

    return out


def propose_metadata_from_mb(
    mb_info: MBInfo | Mapping[str, object],
) -> dict[str, str]:
    out: dict[str, str] = {}
    if not mb_info:
        return out

    title = mb_info.get("recording_title")
    if title:
        out["TIT2"] = str(title)
    artist = mb_info.get("artist")
    if artist:
        out["TPE1"] = str(artist)
    release_title = mb_info.get("release_title")
    if release_title:
        out["TALB"] = str(release_title)

    rid = mb_info.get("recording_id")
    if rid:
        out["TXXX:musicbrainz_recording_id"] = str(rid)
    relid = mb_info.get("release_id")
    if relid:
        out["TXXX:musicbrainz_release_id"] = str(relid)
    prov = mb_info.get("provenance", {})
    if prov:
        out["TXXX:musicbrainz_provenance"] = str(prov)
    return out
