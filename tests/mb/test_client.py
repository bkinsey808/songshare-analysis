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
