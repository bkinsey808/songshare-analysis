import sys
from typing import Any

import pytest

from songshare_analysis.mb.client import musicbrainz_lookup


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
