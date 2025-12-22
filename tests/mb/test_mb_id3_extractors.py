from typing import Any

from songshare_analysis.mb.extractors import _mb_extract_fields


def test_mb_extract_fields_all() -> None:
    rec = {
        "id": "rec-1",
        "title": "Song X",
        "length": 210000,
        "isrc-list": ["US-ABC-12-00001"],
        "artist-credit": [
            {
                "artist": {
                    "id": "art-1",
                    "name": "Artist A",
                    "life-span": {"begin": "1970-01-01", "ended": False},
                    "relations": [{"type": "member", "target": "group-1"}],
                },
            },
        ],
        "tag-list": [{"name": "folk"}],
        "user-tag-list": [{"name": "lovely"}],
        "work-list": [{"id": "work-1", "title": "Work Title"}],
        "relation-list": [{"target": "https://artist.example.com"}],
        "release-list": [
            {
                "id": "rel-1",
                "title": "Rel",
                "date": "2020-01-01",
                "country": "US",
                "release-group": {
                    "primary-type": "Album",
                    "secondary-types": ["Compilation"],
                },
                "label-info-list": [{"label": {"name": "LabelName"}}],
                "relation-list": [{"url": {"resource": "https://release.example.com"}}],
                "medium-list": [{"format": "CD", "position": 1, "track-count": 10}],
            },
        ],
    }
    candidate = {"score": 95}

    out = _mb_extract_fields(rec, candidate)

    assert out["recording_id"] == "rec-1"
    assert out["recording_title"] == "Song X"
    assert out["artist"] == "Artist A"
    assert out["score"] == 95
    assert out["length"] == 210000
    assert out["isrcs"] == ["US-ABC-12-00001"]
    assert out["release_id"] == "rel-1"
    assert out["release_date"] == "2020-01-01"
    assert out["label"] == "LabelName"
    assert out["genres"] == ["folk"]
    assert "https://artist.example.com" in out.get("urls", [])
    assert "https://release.example.com" in out.get("urls", [])
    assert out.get("artist_lifespan", {}).get("begin") == "1970-01-01"
    assert out.get("artist_relations")
    assert out["artist_relations"][0]["type"] == "member"
    assert out["country"] == "US"
    assert out.get("release_group_type") == "Album"
    assert out.get("release_group_secondary_types") == ["Compilation"]
    assert out.get("mediums") and out["mediums"][0]["format"] == "CD"
    assert out.get("work-list") or out.get("works") or out.get("work")
    assert out.get("user_tags") == ["lovely"]
    assert out.get("cover_art") == "https://coverartarchive.org/release/rel-1/front"
    assert not out.get("artist_external_ids")
    assert out.get("rating") is None


def test_mb_extract_fields_ratings_and_external_ids() -> None:
    rec = {
        "id": "rec-3",
        "title": "Rated Song",
        "rating": {"value": 4.2},
        "artist-credit": [
            {
                "artist": {
                    "id": "art-2",
                    "external-ids": [{"type": "discogs", "value": "123"}],
                },
            },
        ],
        "external-ids": [{"type": "spotify", "value": "spotify:123"}],
        "work-list": [{"id": "work-42", "title": "Work X", "iswc": "T-000.000.000-0"}],
    }
    out = _mb_extract_fields(rec, {})
    assert out.get("rating") and out["rating"].get("value") == 4.2
    assert out.get("external_ids")
    assert out["external_ids"].get("spotify") == "spotify:123"
    assert out.get("works") and out["works"][0].get("iswc") == "T-000.000.000-0"


def test_mb_extract_fields_missing_optional() -> None:
    rec = {"id": "rec-2", "title": "No Extras"}
    candidate: dict[str, Any] = {}

    out = _mb_extract_fields(rec, candidate)
    assert out["recording_id"] == "rec-2"
    assert out["recording_title"] == "No Extras"
    assert "isrcs" not in out
    assert "genres" not in out
    assert "urls" not in out
