from songshare_analysis.mb import propose_metadata_from_mb
from songshare_analysis.types import MBInfo


def test_propose_metadata_basic_fields_mb() -> None:
    mb: MBInfo = {
        "recording_title": "Test Song",
        "artist": "The Artist",
        "release_title": "The Album",
        "recording_id": "rec-123",
        "release_id": "rel-456",
        "provenance": {"source": "musicbrainz"},
    }

    proposed = propose_metadata_from_mb(mb)
    assert proposed["TIT2"] == "Test Song"
    assert proposed["TPE1"] == "The Artist"
    assert proposed["TALB"] == "The Album"
    assert proposed["TXXX:musicbrainz_recording_id"] == "rec-123"
    assert proposed["TXXX:musicbrainz_release_id"] == "rel-456"
    assert "TXXX:musicbrainz_provenance" in proposed


def test_propose_metadata_empty_mb() -> None:
    mb: MBInfo = {}
    proposed = propose_metadata_from_mb(mb)
    assert proposed == {}
