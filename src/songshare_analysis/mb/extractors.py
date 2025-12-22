"""Helpers to extract fields from MusicBrainz responses."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import MBInfo


def _extract_isrcs_from(
    rec: Mapping[str, object],
    candidate: Mapping[str, object],
) -> list[str]:
    out_isrcs: list[str] = []
    for k in ("isrc-list", "isrcs"):
        vals = rec.get(k) or candidate.get(k)
        if not vals or not isinstance(vals, list):
            continue
        for v in vals:
            if isinstance(v, str):
                out_isrcs.append(v)
            elif isinstance(v, dict):
                maybe = v.get("id") or v.get("isrc")
                if isinstance(maybe, str):
                    out_isrcs.append(maybe)
    return out_isrcs


def _extract_labels_from_release(rel_obj: Mapping[str, object]) -> list[str]:
    out_labels: list[str] = []
    lab_list = rel_obj.get("label-info-list") or rel_obj.get("label-info") or []
    if isinstance(lab_list, list):
        lst = lab_list
    elif isinstance(lab_list, dict) or isinstance(lab_list, str):
        lst = [lab_list]
    else:
        return out_labels
    for li in lst:
        if isinstance(li, dict):
            lab = li.get("label") or {}
            if isinstance(lab, dict):
                name = lab.get("name") or lab.get("label-name")
                if name:
                    out_labels.append(name)
            elif isinstance(lab, str):
                out_labels.append(lab)
    return out_labels


def _extract_genres_from(rec: Mapping[str, object]) -> list[str]:
    out_g: list[str] = []
    for key in ("tag-list", "genre-list", "tags", "genres"):
        lst = rec.get(key)
        if isinstance(lst, list):
            items = lst
        elif isinstance(lst, dict) or isinstance(lst, str):
            items = [lst]
        else:
            continue
        for t in items:
            if isinstance(t, dict):
                name = t.get("name") or t.get("title")
                if name:
                    out_g.append(name)
            elif isinstance(t, str):
                out_g.append(t)
    return out_g


def _extract_urls_from_rel_list(
    rel_list: Iterable[Mapping[str, object]] | None,
) -> list[str]:
    urls: list[str] = []
    if not rel_list:
        return urls
    for r in rel_list:
        if not isinstance(r, Mapping):
            continue
        tgt = r.get("target")
        if isinstance(tgt, str):
            urls.append(tgt)
            continue
        urlobj = r.get("url")
        if isinstance(urlobj, dict):
            res = urlobj.get("resource") or urlobj.get("id") or urlobj.get("url")
            if isinstance(res, str):
                urls.append(res)
    return urls


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


def _extract_mediums_from_release(rel: Mapping[str, object]) -> list[dict[str, object]]:
    out_m: list[dict[str, object]] = []
    medium_list = rel.get("medium-list") or []
    if not isinstance(medium_list, list):
        return out_m
    for m in medium_list:
        if not isinstance(m, dict):
            continue
        out_m.append(
            {
                "format": m.get("format"),
                "position": m.get("position"),
                "track_count": m.get("track-count") or m.get("track_count"),
            },
        )
    return out_m


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


def _extract_user_tags(rec: Mapping[str, object]) -> list[str]:
    user_tags = rec.get("user-tag-list") or rec.get("user-tags") or rec.get("user-tag")
    if isinstance(user_tags, list):
        items = user_tags
    elif isinstance(user_tags, dict) or isinstance(user_tags, str):
        items = [user_tags]
    else:
        return []
    out_user: list[str] = []
    for t in items:
        if isinstance(t, dict):
            name = t.get("name") or t.get("title")
            if name:
                out_user.append(name)
        elif isinstance(t, str):
            out_user.append(t)
    return out_user


def _populate_genres(out: MBInfo, rec: Mapping[str, object]) -> None:
    genres = _extract_genres_from(rec)
    if genres:
        out["genres"] = genres

    user_tags = _extract_user_tags(rec)
    if user_tags:
        out["user_tags"] = user_tags


def _extract_external_ids(entity: Mapping[str, object]) -> dict[str, str]:
    out_ids: dict[str, str] = {}
    for key in ("external-ids", "external-id-list", "external-ids-list"):
        lst = entity.get(key)
        if not lst or not isinstance(lst, list):
            continue
        for e in lst:
            if not isinstance(e, dict):
                continue
            typ = e.get("type") or e.get("id") or e.get("external-id-type")
            val = e.get("value") or e.get("id") or e.get("external-id-value")
            if typ and val:
                out_ids[str(typ)] = str(val)
    return out_ids


def _extract_release_urls(rec: Mapping[str, object]) -> list[str]:
    u: list[str] = []
    releases = rec.get("release-list") or []
    if not isinstance(releases, list):
        return u
    for rel in releases:
        if not isinstance(rel, dict):
            continue
        rel_rels = rel.get("relation-list") or rel.get("relations") or []
        if not isinstance(rel_rels, list):
            continue
        u.extend(_extract_urls_from_rel_list(rel_rels))
    return u


def _extract_works_from(rec: Mapping[str, object]) -> list[dict[str, object]]:
    out_w: list[dict[str, object]] = []
    for key in ("work-list", "work-relation-list", "work-rels", "works"):
        lst = rec.get(key)
        if not lst or not isinstance(lst, list):
            continue
        for w in lst:
            if isinstance(w, dict):
                entry: dict[str, object] = {}
                idv = w.get("id")
                if idv is not None:
                    entry["id"] = idv
                tv = w.get("title")
                if tv is not None:
                    entry["title"] = tv
                if w.get("iswc"):
                    entry["iswc"] = w.get("iswc")
                out_w.append(entry)
            elif isinstance(w, str):
                out_w.append({"title": w})
    return out_w


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
