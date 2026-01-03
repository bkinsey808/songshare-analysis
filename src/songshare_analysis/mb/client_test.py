import sys
from typing import Any

import pytest

from songshare_analysis.mb.client import musicbrainz_lookup


class FakeMB:
    def __init__(self) -> None:
        self._user: tuple[str, str, str] | None = None

    def set_useragent(self, app: str, version: str, contact: str) -> None:
        self._user = (app, version, contact)

    def search_recordings(self, limit: int = 3, **kwargs: Any) -> dict[str, Any]:
        # Return a fake recording-list if title contains 'Om'
        if kwargs.get("recording") and "Om" in kwargs["recording"]:
            return {
                "recording-list": [
                    {"id": "rec-1", "title": kwargs["recording"], "score": 95},
                ],
            }
        return {"recording-list": []}

    def get_recording_by_id(self, rec_id: str, includes: Any = None) -> dict[str, Any]:
        return {
            "recording": {
                "id": rec_id,
                "title": "Om Nama Shivaya",
                "artist-credit": [{"name": "Raphael"}],
                "release-list": [{"id": "rel-1", "title": "Soundcloud"}],
            },
        }


@pytest.mark.skipif(sys.platform == "win32", reason="Network tests skipped on Windows")
def test_musicbrainz_lookup_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMB()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Om Nama Shivaya", "TPE1": "Raphael"}
    res = musicbrainz_lookup(tags)

    assert res.get("recording_id") == "rec-1"
    assert res.get("recording_title") == "Om Nama Shivaya"
    assert res.get("artist") == "Raphael"
    assert res.get("release_title") == "Soundcloud"
    # Cover art should be present for precise (title+artist) matches
    assert res.get("cover_art") == "https://coverartarchive.org/release/rel-1/front"


class FakeMBMulti:
    def set_useragent(self, app: str, version: str, contact: str) -> None:
        pass

    def search_recordings(self, limit: int = 3, **kwargs: Any) -> dict[str, Any]:
        # Return multiple candidates to test selection logic
        # Candidate A: exact title match (lower score)
        # Candidate B: fuzzy title (higher score)
        recs = [
            {"id": "rec-exact", "title": kwargs.get("recording"), "score": 50},
            {
                "id": "rec-fuzzy",
                "title": f"{kwargs.get('recording')} (live)",
                "score": 95,
            },
        ]
        return {"recording-list": recs}

    def get_recording_by_id(self, rec_id: str, includes: Any = None) -> dict[str, Any]:
        return {
            "recording": {
                "id": rec_id,
                "title": "dummy",
                "artist-credit": [{"name": "Artist"}],
                "release-list": [{"id": "rel-1", "title": "Rel"}],
            }
        }


class FakeMBFuzzy:
    """Returns candidates that do not exactly match the provided title/artist."""

    def set_useragent(self, app: str, version: str, contact: str) -> None:
        pass

    def search_recordings(self, limit: int = 3, **kwargs: Any) -> dict[str, Any]:
        recs = [
            {
                "id": "rec-live",
                "title": f"{kwargs.get('recording')} (live)",
                "artist-credit": [{"name": "Someone Else"}],
                "score": 95,
            }
        ]
        return {"recording-list": recs}

    def get_recording_by_id(self, rec_id: str, includes: Any = None) -> dict[str, Any]:
        return {
            "recording": {
                "id": rec_id,
                "title": "dummy",
                "artist-credit": [{"name": "Someone Else"}],
                "release-list": [{"id": "rel-live", "title": "Live Rel"}],
            }
        }


class FakeMBArtist:
    def set_useragent(self, app: str, version: str, contact: str) -> None:
        pass

    def search_recordings(self, limit: int = 3, **kwargs: Any) -> dict[str, Any]:
        # Two candidates; one matches artist exactly
        recs = [
            {
                "id": "rec-a",
                "title": kwargs.get("recording"),
                "artist-credit": [{"name": "Correct"}],
                "score": 80,
            },
            {
                "id": "rec-b",
                "title": kwargs.get("recording"),
                "artist-credit": [{"name": "Wrong"}],
                "score": 95,
            },
        ]
        return {"recording-list": recs}

    def get_recording_by_id(self, rec_id: str, includes: Any = None) -> dict[str, Any]:
        return {
            "recording": {
                "id": rec_id,
                "title": "dummy",
                "artist-credit": [
                    {"name": "Correct" if rec_id == "rec-a" else "Wrong"}
                ],
                "release-list": [{"id": "rel-1", "title": "Rel"}],
            }
        }


class FakeMBTie:
    def set_useragent(self, app: str, version: str, contact: str) -> None:
        pass

    def search_recordings(self, limit: int = 3, **kwargs: Any) -> dict[str, Any]:
        # Two candidates with identical score; ids differ. Deterministic
        # selection should pick the one with lexicographically smaller id.
        recs = [
            {"id": "rec-b", "title": kwargs.get("recording"), "score": 90},
            {"id": "rec-a", "title": kwargs.get("recording"), "score": 90},
        ]
        return {"recording-list": recs}

    def get_recording_by_id(self, rec_id: str, includes: Any = None) -> dict[str, Any]:
        return {
            "recording": {
                "id": rec_id,
                "title": "dummy",
                "artist-credit": [{"name": "Artist"}],
                "release-list": [{"id": "rel-1", "title": "Rel"}],
            }
        }


@pytest.mark.skipif(sys.platform == "win32", reason="Network tests skipped on Windows")
def test_prefers_exact_title_over_higher_score(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMBMulti()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Test Song", "TPE1": "Artist"}
    res = musicbrainz_lookup(tags)

    # exact-title candidate should be chosen despite lower score
    assert res.get("recording_id") == "rec-exact"


@pytest.mark.skipif(sys.platform == "win32", reason="Network tests skipped on Windows")
def test_prefers_exact_artist_when_title_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeMBArtist()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Some Song", "TPE1": "Correct"}
    res = musicbrainz_lookup(tags)

    # Candidate with matching artist should be selected even if it has lower score
    assert res.get("recording_id") == "rec-a"


@pytest.mark.skipif(sys.platform == "win32", reason="Network tests skipped on Windows")
def test_tie_break_uses_smallest_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMBTie()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Tie Song", "TPE1": "Artist"}
    res = musicbrainz_lookup(tags)

    # Expect 'rec-a' (lexicographically smaller) to be chosen when scores equal
    assert res.get("recording_id") == "rec-a"


@pytest.mark.skipif(sys.platform == "win32", reason="Network tests skipped on Windows")
def test_cover_art_absent_for_fuzzy_match(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMBFuzzy()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Some Song", "TPE1": "Artist"}
    res = musicbrainz_lookup(tags)

    # Candidate exists but is not a precise title+artist match, so cover_art
    # should be omitted to avoid mismatched album art.
    assert "cover_art" not in res


@pytest.mark.skipif(sys.platform == "win32", reason="Network tests skipped on Windows")
def test_cover_art_absent_for_fuzzy_title_only(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMBFuzzy()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Some Song"}
    res = musicbrainz_lookup(tags)

    # When only title provided and the found recording title is fuzzy, do not
    # supply cover_art.
    assert "cover_art" not in res


@pytest.mark.skipif(sys.platform == "win32", reason="Network tests skipped on Windows")
def test_cover_art_present_for_exact_title_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeMBMulti()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Test Song"}
    res = musicbrainz_lookup(tags)

    assert res.get("cover_art") == "https://coverartarchive.org/release/rel-1/front"
