from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .basic import (
    _extract_external_ids,
    _extract_genres_from,
    _extract_isrcs_from,
    _extract_labels_from_release,
    _extract_mediums_from_release,
    _extract_release_urls,
    _extract_urls_from_rel_list,
    _extract_user_tags,
    _extract_works_from,
)

if TYPE_CHECKING:
    from songshare_analysis.types import MBInfo


def _populate_basic_fields(
    out: MBInfo,
    rec: Mapping[str, object],
    candidate: Mapping[str, object],
) -> None:
    id_val = rec.get("id")
    if isinstance(id_val, str):
        out["recording_id"] = id_val

    title_val = rec.get("title")
    if title_val is not None:
        out["recording_title"] = str(title_val)

    if "score" in candidate:
        s = candidate.get("score")
        if isinstance(s, (int, float, str)):
            out["score"] = s
    elif candidate.get("ext-score"):
        s = candidate.get("ext-score")
        if isinstance(s, (int, float, str)):
            out["score"] = s

    artists = rec.get("artist-credit") or []
    if isinstance(artists, list) and artists:
        first = artists[0]
        if isinstance(first, dict):
            name = first.get("name") or first.get("artist", {}).get("name")
            if name:
                out["artist"] = str(name)
        else:
            out["artist"] = str(first)


def _populate_recording_fields(
    out: MBInfo,
    rec: Mapping[str, object],
    candidate: Mapping[str, object],
) -> None:
    length = rec.get("length") or candidate.get("length")
    if isinstance(length, (int, float)):
        out["length"] = length
    isrcs = _extract_isrcs_from(rec, candidate)
    if isrcs:
        out["isrcs"] = isrcs

    rating = rec.get("rating") or candidate.get("rating")
    if rating and isinstance(rating, dict) and rating.get("value") is not None:
        out["rating"] = rating

    ext_ids = _extract_external_ids(rec)
    if ext_ids:
        out["external_ids"] = ext_ids


def _populate_release_group_fields(out: MBInfo, rg: object) -> None:
    if not isinstance(rg, dict):
        return
    ptype = rg.get("primary-type") or rg.get("type")
    if ptype:
        out["release_group_type"] = ptype
    sec = rg.get("secondary-types")
    if sec:
        out["release_group_secondary_types"] = sec


def _populate_release_fields(out: MBInfo, rec: Mapping[str, object]) -> None:
    releases = rec.get("release-list") or []
    if not releases or not isinstance(releases, list):
        return
    rel = releases[0]
    if not isinstance(rel, dict):
        return
    title = rel.get("title")
    if isinstance(title, str):
        out["release_title"] = title
    rid = rel.get("id")
    if isinstance(rid, str):
        out["release_id"] = rid
    date = rel.get("date") or rel.get("release-date")
    if isinstance(date, str):
        out["release_date"] = date
    labels = _extract_labels_from_release(rel)
    if labels:
        out["label"] = labels[0] if len(labels) == 1 else labels

    country = rel.get("country")
    if isinstance(country, str):
        out["country"] = country

    rg = rel.get("release-group") or {}
    _populate_release_group_fields(out, rg)

    mediums = _extract_mediums_from_release(rel)
    if mediums:
        out["mediums"] = mediums

    rel_id = rel.get("id")
    if rel_id:
        out["cover_art"] = f"https://coverartarchive.org/release/{rel_id}/front"


def _populate_genres(out: MBInfo, rec: Mapping[str, object]) -> None:
    genres = _extract_genres_from(rec)
    if genres:
        out["genres"] = genres

    user_tags = _extract_user_tags(rec)
    if user_tags:
        out["user_tags"] = user_tags


def _populate_urls(out: MBInfo, rec: Mapping[str, object]) -> None:
    urls: list[str] = []
    rels = rec.get("relation-list") or rec.get("relations") or []
    if isinstance(rels, list):
        urls.extend(_extract_urls_from_rel_list(rels))
    urls.extend(_extract_release_urls(rec))
    if urls:
        out["urls"] = urls

    works = _extract_works_from(rec)
    if works:
        out["works"] = works


def _populate_artist_meta(  # noqa: C901 (parsing varied response shapes)
    out: MBInfo,
    rec: Mapping[str, object],
) -> None:
    artists = rec.get("artist-credit") or []
    if not isinstance(artists, list) or not artists:
        return

    first = artists[0]
    artist_obj = None
    if isinstance(first, dict):
        artist_obj = first.get("artist") or first
    if not isinstance(artist_obj, dict):
        return

    if artist_obj.get("id"):
        aid = artist_obj.get("id")
        if isinstance(aid, str):
            out["artist_id"] = aid
    if artist_obj.get("sort-name"):
        sname = artist_obj.get("sort-name")
        if sname is not None:
            out["artist_sort_name"] = str(sname)
    if artist_obj.get("disambiguation"):
        dis = artist_obj.get("disambiguation")
        if dis is not None:
            out["artist_disambiguation"] = str(dis)
    alias_list = artist_obj.get("alias-list") or artist_obj.get("aliases") or []
    if alias_list:
        out_aliases: list[str] = []
        for a in alias_list:
            if isinstance(a, dict):
                n = a.get("alias") or a.get("name")
                if n:
                    out_aliases.append(n)
            elif isinstance(a, str):
                out_aliases.append(a)
        if out_aliases:
            out["artist_aliases"] = out_aliases

    span = artist_obj.get("life-span")
    if span:
        out["artist_lifespan"] = span

    ext_ids = _extract_external_ids(artist_obj)
    if ext_ids:
        out["artist_external_ids"] = ext_ids

    rels = artist_obj.get("relations") or artist_obj.get("relation-list")
    if not rels or not isinstance(rels, list):
        return

    out_rels: list[dict[str, object]] = []
    for r in rels:
        if not isinstance(r, dict):
            continue
        tgt = r.get("target") or r.get("id") or r.get("url") or r.get("resource")
        out_rels.append({"type": r.get("type"), "target": tgt})
    if out_rels:
        out["artist_relations"] = out_rels
