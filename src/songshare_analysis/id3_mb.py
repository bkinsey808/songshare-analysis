"""MusicBrainz lookup and extraction helpers factored out of `id3.py`.

Exports `musicbrainz_lookup` and `propose_metadata_from_mb` along with
internal helpers used to extract fields from varied MusicBrainz responses.
"""

from __future__ import annotations

import importlib
import os
from typing import Any, Dict


def musicbrainz_lookup(tags: Dict[str, str]) -> Dict[str, Any]:
    title = tags.get("TIT2")
    artist = tags.get("TPE1")
    if not (title or artist):
        return {}

    try:
        mb = importlib.import_module("musicbrainzngs")
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError(
            "musicbrainzngs is required for MusicBrainz lookups."
            " Install with `pip install musicbrainzngs`"
        ) from exc

    contact = os.environ.get("MUSICBRAINZ_CONTACT", "songshare@example.com")
    try:
        mb.set_useragent("songshare-analysis", "0.1", contact)
    except Exception:
        pass

    kwargs: Dict[str, str] = {}
    if title:
        kwargs["recording"] = title
    if artist:
        kwargs["artist"] = artist

    recs = _mb_search(mb, kwargs)
    if not recs:
        return {}

    candidate = recs[0]
    rec_id = candidate.get("id")
    if not rec_id:
        return {}

    full = _mb_get_recording_safe(mb, rec_id, candidate)

    rec = full.get("recording", candidate)
    return _mb_extract_fields(rec, candidate)


def _mb_search(mb: Any, kwargs: Dict[str, str]) -> list[Dict[str, Any]]:
    try:
        res = mb.search_recordings(limit=3, **kwargs)
    except Exception:
        return []
    return res.get("recording-list") or []


def _mb_get_recording_safe(
    mb: Any,
    rec_id: str,
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        return mb.get_recording_by_id(
            rec_id,
            includes=["artists", "releases"],
        ) or {"recording": candidate}
    except Exception:
        return {"recording": candidate}


# --- Field extraction helpers ---


def _extract_isrcs_from(rec: Dict[str, Any], candidate: Dict[str, Any]) -> list[str]:
    out_isrcs: list[str] = []
    for k in ("isrc-list", "isrcs"):
        vals = rec.get(k) or candidate.get(k)
        if not vals:
            continue
        for v in vals:
            if isinstance(v, str):
                out_isrcs.append(v)
            elif isinstance(v, dict):
                maybe = v.get("id") or v.get("isrc")
                if isinstance(maybe, str):
                    out_isrcs.append(maybe)
    return out_isrcs


def _extract_labels_from_release(rel_obj: Dict[str, Any]) -> list[str]:
    out_labels: list[str] = []
    for li in rel_obj.get("label-info-list") or rel_obj.get("label-info") or []:
        if isinstance(li, dict):
            lab = li.get("label") or {}
            if isinstance(lab, dict):
                name = lab.get("name") or lab.get("label-name")
                if name:
                    out_labels.append(name)
            elif isinstance(lab, str):
                out_labels.append(lab)
    return out_labels


def _extract_genres_from(rec: Dict[str, Any]) -> list[str]:
    out_g: list[str] = []
    for key in ("tag-list", "genre-list", "tags", "genres"):
        lst = rec.get(key)
        if not lst:
            continue
        for t in lst:
            if isinstance(t, dict):
                name = t.get("name") or t.get("title")
                if name:
                    out_g.append(name)
            elif isinstance(t, str):
                out_g.append(t)
    return out_g


def _extract_urls_from_rel_list(rel_list: Any) -> list[str]:
    urls: list[str] = []
    if not rel_list:
        return urls
    for r in rel_list:
        if not isinstance(r, dict):
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
    out: Dict[str, Any], rec: Dict[str, Any], candidate: Dict[str, Any]
) -> None:
    out["recording_id"] = rec.get("id")
    out["recording_title"] = rec.get("title")
    if "score" in candidate:
        out["score"] = candidate.get("score")
    elif candidate.get("ext-score"):
        out["score"] = candidate.get("ext-score")

    artists = rec.get("artist-credit") or []
    if isinstance(artists, list) and artists:
        first = artists[0]
        if isinstance(first, dict):
            out["artist"] = first.get("name") or first.get("artist", {}).get("name")
        else:
            out["artist"] = str(first)


def _populate_recording_fields(
    out: Dict[str, Any], rec: Dict[str, Any], candidate: Dict[str, Any]
) -> None:
    length = rec.get("length") or candidate.get("length")
    if length:
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


def _extract_mediums_from_release(rel: Dict[str, Any]) -> list[Dict[str, Any]]:
    out_m: list[Dict[str, Any]] = []
    for m in rel.get("medium-list") or []:
        if not isinstance(m, dict):
            continue
        out_m.append(
            {
                "format": m.get("format"),
                "position": m.get("position"),
                "track_count": m.get("track-count") or m.get("track_count"),
            }
        )
    return out_m


def _populate_release_fields(out: Dict[str, Any], rec: Dict[str, Any]) -> None:
    releases = rec.get("release-list") or []
    if not releases:
        return
    rel = releases[0]
    out["release_title"] = rel.get("title")
    out["release_id"] = rel.get("id")
    date = rel.get("date") or rel.get("release-date")
    if date:
        out["release_date"] = date
    labels = _extract_labels_from_release(rel)
    if labels:
        out["label"] = labels[0] if len(labels) == 1 else labels

    country = rel.get("country")
    if country:
        out["country"] = country

    rg = rel.get("release-group") or {}
    if rg:
        ptype = rg.get("primary-type") or rg.get("type")
        if ptype:
            out["release_group_type"] = ptype
        sec = rg.get("secondary-types")
        if sec:
            out["release_group_secondary_types"] = sec

    mediums = _extract_mediums_from_release(rel)
    if mediums:
        out["mediums"] = mediums

    rel_id = rel.get("id")
    if rel_id:
        out["cover_art"] = f"https://coverartarchive.org/release/{rel_id}/front"


def _populate_genres(out: Dict[str, Any], rec: Dict[str, Any]) -> None:
    genres = _extract_genres_from(rec)
    if genres:
        out["genres"] = genres

    user_tags = rec.get("user-tag-list") or rec.get("user-tags") or rec.get("user-tag")
    if user_tags:
        out_user: list[str] = []
        for t in user_tags:
            if isinstance(t, dict):
                name = t.get("name") or t.get("title")
                if name:
                    out_user.append(name)
            elif isinstance(t, str):
                out_user.append(t)
        if out_user:
            out["user_tags"] = out_user


def _extract_external_ids(entity: Dict[str, Any]) -> dict[str, str]:
    out_ids: dict[str, str] = {}
    for key in ("external-ids", "external-id-list", "external-ids-list"):
        lst = entity.get(key)
        if not lst:
            continue
        for e in lst:
            if not isinstance(e, dict):
                continue
            typ = e.get("type") or e.get("id") or e.get("external-id-type")
            val = e.get("value") or e.get("id") or e.get("external-id-value")
            if typ and val:
                out_ids[str(typ)] = str(val)
    return out_ids


def _extract_release_urls(rec: Dict[str, Any]) -> list[str]:
    u: list[str] = []
    for rel in rec.get("release-list") or []:
        u.extend(
            _extract_urls_from_rel_list(
                rel.get("relation-list") or rel.get("relations") or []
            )
        )
    return u


def _extract_works_from(rec: Dict[str, Any]) -> list[dict[str, Any]]:
    out_w: list[dict[str, Any]] = []
    for key in ("work-list", "work-relation-list", "work-rels", "works"):
        lst = rec.get(key)
        if not lst:
            continue
        for w in lst:
            if isinstance(w, dict):
                entry = {"id": w.get("id"), "title": w.get("title")}
                if w.get("iswc"):
                    entry["iswc"] = w.get("iswc")
                out_w.append(entry)
            elif isinstance(w, str):
                out_w.append({"title": w})
    return out_w


def _populate_urls(out: Dict[str, Any], rec: Dict[str, Any]) -> None:
    urls: list[str] = []
    urls.extend(
        _extract_urls_from_rel_list(
            rec.get("relation-list") or rec.get("relations") or []
        )
    )
    urls.extend(_extract_release_urls(rec))
    if urls:
        out["urls"] = urls

    works = _extract_works_from(rec)
    if works:
        out["works"] = works


def _populate_artist_meta(  # noqa: C901 (parsing varied response shapes)
    out: Dict[str, Any], rec: Dict[str, Any]
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
        out["artist_id"] = artist_obj.get("id")
    if artist_obj.get("sort-name"):
        out["artist_sort_name"] = artist_obj.get("sort-name")
    if artist_obj.get("disambiguation"):
        out["artist_disambiguation"] = artist_obj.get("disambiguation")
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
    if not rels:
        return

    out_rels: list[dict[str, Any]] = []
    for r in rels:
        if not isinstance(r, dict):
            continue
        tgt = r.get("target") or r.get("id") or r.get("url") or r.get("resource")
        out_rels.append({"type": r.get("type"), "target": tgt})
    if out_rels:
        out["artist_relations"] = out_rels


def _mb_extract_fields(
    rec: Dict[str, Any], candidate: Dict[str, Any]
) -> Dict[str, Any]:
    out: Dict[str, Any] = {"provenance": {"source": "musicbrainz"}}

    _populate_basic_fields(out, rec, candidate)
    _populate_recording_fields(out, rec, candidate)
    _populate_release_fields(out, rec)
    _populate_genres(out, rec)
    _populate_urls(out, rec)
    _populate_artist_meta(out, rec)

    return out


def propose_metadata_from_mb(mb_info: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not mb_info:
        return out

    if mb_info.get("recording_title"):
        out["TIT2"] = str(mb_info["recording_title"])
    if mb_info.get("artist"):
        out["TPE1"] = str(mb_info["artist"])
    if mb_info.get("release_title"):
        out["TALB"] = str(mb_info["release_title"])

    if mb_info.get("recording_id"):
        out["TXXX:musicbrainz_recording_id"] = str(mb_info["recording_id"])
    if mb_info.get("release_id"):
        out["TXXX:musicbrainz_release_id"] = str(mb_info["release_id"])
    out["TXXX:musicbrainz_provenance"] = str(mb_info.get("provenance", {}))
    return out
