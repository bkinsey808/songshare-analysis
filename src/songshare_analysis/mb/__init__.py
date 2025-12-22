"""Public exports for musicbrainz helpers."""

from __future__ import annotations

from .client import musicbrainz_lookup
from .extractors import _mb_extract_fields, propose_metadata_from_mb

__all__ = ["_mb_extract_fields", "musicbrainz_lookup", "propose_metadata_from_mb"]
