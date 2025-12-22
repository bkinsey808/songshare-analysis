import sys
from typing import Any

import pytest

from songshare_analysis.mb.client import musicbrainz_lookup


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
def test_tie_break_uses_smallest_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMBTie()
    monkeypatch.setitem(sys.modules, "musicbrainzngs", fake)

    tags = {"TIT2": "Tie Song", "TPE1": "Artist"}
    res = musicbrainz_lookup(tags)

    # Expect 'rec-a' (lexicographically smaller) to be chosen when scores equal
    assert res.get("recording_id") == "rec-a"
