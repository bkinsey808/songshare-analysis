"""MusicBrainz client helpers and high-level lookup function."""

from __future__ import annotations

import contextlib
import importlib
import os
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from songshare_analysis.types import MBInfo, MusicBrainzClient


def musicbrainz_lookup(tags: dict[str, str]) -> MBInfo:
    """Lookup recording by title/artist and return extracted MBInfo.

    This mirrors the older `id3_mb.musicbrainz_lookup` behaviour but lives in
    its own module so extraction logic can be tested separately.
    """
    title = tags.get("TIT2")
    artist = tags.get("TPE1")
    if not (title or artist):
        return {}

    try:
        mb = importlib.import_module("musicbrainzngs")
    except ImportError as exc:  # pragma: no cover - runtime dependency
        msg = (
            "musicbrainzngs is required for MusicBrainz lookups."
            " Install with `pip install musicbrainzngs`"
        )
        raise RuntimeError(msg) from exc

    contact = os.environ.get("MUSICBRAINZ_CONTACT", "songshare@example.com")
    with contextlib.suppress(Exception):
        mb.set_useragent("songshare-analysis", "0.1", contact)

    # importlib returns a module object; cast to our protocol for type-checking
    mb_client = cast("MusicBrainzClient", mb)

    candidate = _find_best_recording(mb_client, title, artist)
    if not candidate:
        return {}

    rec_id = candidate.get("id")
    if not rec_id or not isinstance(rec_id, str):
        return {}

    full = _mb_get_recording_safe(mb_client, rec_id, candidate)

    rec = full.get("recording") or candidate
    if not isinstance(rec, dict):
        rec = candidate

    # Import extraction at runtime to avoid circular imports
    from .extractors import _mb_extract_fields

    out = _mb_extract_fields(rec, candidate)

    # Only include cover art when the selected candidate is a precise match.
    # Precise rules:
    #  - If both title and artist were provided, require exact match on both.
    #  - If only one of title/artist provided, require an exact match on that field.
    # Use the **search candidate** for precision checks — the full `recording`
    # payload returned by `get_recording_by_id` may include normalized/altered
    # fields (e.g., a generic "dummy" title) that would cause exact-match
    # checks to fail in cases where the search result was actually precise.
    if not _is_precise_match(title, artist, candidate, rec):
        out.pop("cover_art", None)

    return out


def _mb_search(
    mb: MusicBrainzClient,
    kwargs: dict[str, str],
) -> list[dict[str, object]]:
    try:
        res = mb.search_recordings(limit=3, **kwargs)
    except Exception:  # noqa: BLE001
        return []
    lst = res.get("recording-list")
    if not isinstance(lst, list):
        return []
    # Filter to dicts only so callers can rely on mapping shapes
    return [r for r in lst if isinstance(r, dict)]


def _mb_get_recording_safe(
    mb: MusicBrainzClient,
    rec_id: str,
    candidate: dict[str, object],
) -> dict[str, object]:
    try:
        return mb.get_recording_by_id(
            rec_id,
            includes=["artists", "releases"],
        ) or {"recording": candidate}
    except Exception:  # noqa: BLE001
        return {"recording": candidate}


# Helper utilities for deterministic candidate selection.
def _normalize(s: str | None) -> str:
    return (s or "").strip().casefold()


def _candidate_artist_name(candidate: dict[str, object]) -> str | None:
    ac = candidate.get("artist-credit") or candidate.get("artist")
    if isinstance(ac, list) and ac:
        first = ac[0]
        if isinstance(first, dict):
            return first.get("name")
    if isinstance(ac, dict):
        return ac.get("name")
    if isinstance(ac, str):
        return ac
    return None


def _score(candidate: dict[str, object]) -> int:
    val = candidate.get("score")
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        try:
            return int(val)
        except Exception:
            return 0
    return 0


def _candidate_title(cand: dict[str, object]) -> str | None:
    t = cand.get("title")
    return t if isinstance(t, str) else None


def _is_precise_match(
    title_in: str | None,
    artist_in: str | None,
    candidate_obj: dict[str, object],
    full_obj: dict[str, object] | None = None,
) -> bool:
    """Return True when the found recording is an exact match for the
    provided title/artist according to the project's precision policy.

    This prefers the lightweight `candidate_obj` (the search result) for
    title comparisons. When artist information is missing in the search
    candidate (which is common), fall back to the `full_obj` returned by
    ``get_recording_by_id`` for artist comparisons.
    """
    t_norm = _normalize(title_in)
    a_norm = _normalize(artist_in)

    cand_t = _normalize(_candidate_title(candidate_obj))
    cand_a = _normalize(_candidate_artist_name(candidate_obj))

    if not cand_a and full_obj is not None:
        # Fall back to the more complete record for artist matching
        cand_a = _normalize(_candidate_artist_name(full_obj))

    if title_in and artist_in:
        return cand_t == t_norm and cand_a == a_norm
    if title_in:
        return cand_t == t_norm
    if artist_in:
        return cand_a == a_norm
    return False


def _find_best_recording(
    client: MusicBrainzClient, title_in: str | None, artist_in: str | None
) -> dict[str, object] | None:
    kwargs: dict[str, str] = {}
    if title_in:
        kwargs["recording"] = title_in
    if artist_in:
        kwargs["artist"] = artist_in

    recs = _mb_search(client, kwargs)
    if not recs:
        return None

    # Reuse the selection helper for deterministic behavior
    return _select_candidate(recs, title_in, artist_in)


def _select_candidate(
    recs_in: list[dict[str, object]],
    title_in: str | None,
    artist_in: str | None,
) -> dict[str, object]:
    """Select best candidate deterministically.

    Preference order:
      1. Exact title match(s) (case-insensitive). If artist is present prefer
         those that also exactly match artist.
      2. Exact artist matches (if no exact title match)
      3. Otherwise fall back to highest score.

    On ties (equal score) choose the candidate with the lexicographically
    smallest `id` to make behavior deterministic across runs.
    """

    def _best_by_score_and_id(cands: list[dict[str, object]]) -> dict[str, object]:
        # Use (-score, id) as the sorting key so higher score is preferred and
        # ties are broken by smallest id lexicographically.
        def _key(r: dict[str, object]) -> tuple[int, str]:
            return (-_score(r), str(r.get("id") or ""))

        return min(cands, key=_key)

    t_norm = _normalize(title_in)
    a_norm = _normalize(artist_in)

    exact_title = [r for r in recs_in if _normalize(_candidate_title(r)) == t_norm]
    if exact_title:
        if artist_in:
            exact_title_artist = [
                r
                for r in exact_title
                if _normalize(_candidate_artist_name(r)) == a_norm
            ]
            if exact_title_artist:
                return _best_by_score_and_id(exact_title_artist)
            return _best_by_score_and_id(exact_title)
        return _best_by_score_and_id(exact_title)

    if artist_in:
        exact_artist = [
            r for r in recs_in if _normalize(_candidate_artist_name(r)) == a_norm
        ]
        if exact_artist:
            return _best_by_score_and_id(exact_artist)
    return _best_by_score_and_id(recs_in)
