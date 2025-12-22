from __future__ import annotations

from collections.abc import Iterable, Mapping


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
