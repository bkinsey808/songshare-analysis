"""Lightweight shared typing helpers for songshare-analysis.

This module contains structural typing (Protocols) and small types that
are convenient to share across modules without bringing in heavy
runtime dependencies.

In particular, `ID3Like` captures a *minimal* set of methods that we
actually rely on from the Mutagen ID3 objects. Mutagen does not ship
complete type stubs for the runtime objects we use, which caused the
project to accumulate `Any` usages and take noisy type-checker errors.

Why a Protocol?
- A Protocol lets us express the *shape* of the object we expect (duck
  typing) without requiring an explicit concrete base class.
- It documents the subset of methods we use (`get`, `getall`, `add`,
  `save`, `items`) and improves static checking at call sites.
- We keep the signatures permissive (using `*args, **kwargs`) for
  `add`/`save` so typing stays compatible with a few different
  runtime shapes that Mutagen exposes.

How to use:
- At runtime nothing changes; `cast("ID3Like", obj)` is a no-op that
  tells the type checker to treat `obj` as the protocol. Prefer using
  `cast(...)` close to the boundary where you call into an untyped
  library (the constructor call), rather than sprinkling `Any`.

Examples:
    # in a module that calls the untyped constructor
    tags = cast("ID3Like", ID3(str(path)))
    if tags.getall("APIC"):
        ...

Notes:
- Keep this Protocol minimal; if we need more functionality later we can
  expand it here so the rest of the codebase benefits from the single
  source of truth.

"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, TypedDict


class MBInfo(TypedDict, total=False):
    """TypedDict representing MusicBrainz-derived metadata fields.

    Keys are optional because MusicBrainz responses vary in shape and
    richness. We place this TypedDict here so it can be imported across
    modules (CLI helpers, tests, and the MusicBrainz parsing module)
    without creating import cycles.
    """

    recording_id: str
    recording_title: str
    artist: str
    release_title: str
    release_id: str
    provenance: dict[str, object]
    length: int | float
    isrcs: list[str]
    rating: dict[str, object]
    external_ids: dict[str, str]
    release_date: str
    label: str | list[str]
    country: str
    release_group_type: str
    release_group_secondary_types: list[str]
    mediums: list[dict[str, object]]
    cover_art: str
    genres: list[str]
    user_tags: list[str]
    artist_relations: list[dict[str, object]]
    artist_id: str
    artist_sort_name: str
    artist_disambiguation: str
    artist_aliases: list[str]
    artist_lifespan: dict[str, object]
    artist_external_ids: dict[str, str]
    urls: list[str]
    works: list[dict[str, object]]
    score: int | float | str | None


# Type alias for values stored in ID3 tag frames. Kept here so other
# modules can import a single authoritative definition for what a tag
# value may be (text, binary, or a small list of strings).
TagValue = str | bytes | bytearray | list[str]


class ID3ReadResult(TypedDict):
    """Return shape for ID3 read helpers.

    - ``path``: file path string
    - ``tags``: mapping of frame key -> TagValue
    - ``info``: metadata dictionary (length, bitrate, etc.)
    """

    path: str
    tags: dict[str, TagValue]
    info: dict[str, object]


class ID3Like(Protocol):
    """Minimal structural type for objects that behave like Mutagen ID3.

    This protocol intentionally declares only the methods used by the
    rest of the codebase. The signatures intentionally accept
    ``*args, **kwargs`` where Mutagen's runtime signatures differ in
    parameter names or optional arguments.
    """

    def get(self, key: str) -> Any: ...

    def getall(self, key: str) -> list[Any]: ...

    def add(self, frame: Any, *args: Any, **kwargs: Any) -> None: ...

    def save(self, *args: Any, **kwargs: Any) -> None: ...

    def items(self) -> Iterable[tuple[str, Any]]: ...


class MusicBrainzClient(Protocol):
    """Minimal protocol for the subset of the musicbrainzngs API used in
    the MusicBrainz helpers.

    Kept minimal on purpose — a structural type so modules can `cast(...)`
    the imported module for type checking at the call site.
    """

    def set_useragent(self, app: str, version: str, contact: str) -> None: ...

    def search_recordings(
        self,
        *,
        limit: int = 3,
        **kwargs: str,
    ) -> dict[str, object]: ...

    def get_recording_by_id(
        self,
        rec_id: str,
        includes: list[str] | None = None,
    ) -> dict[str, object] | None: ...


class ErrorLoggerLike(Protocol):
    """Structural protocol for objects that provide an ``error(...)`` method.

    This captures the minimal subset we need for logging error messages from
    helpers (keeps the runtime dependency on the standard ``logging`` module
    optional for callers).
    """

    def error(self, fmt: str, *args: object) -> None: ...


class LoggerLike(ErrorLoggerLike, Protocol):
    """Like ``logging.Logger`` but intentionally minimal and permissive for
    the test/dummy loggers used in the CLI helpers.
    """

    def info(self, msg: object, *args: object, **kwargs: object) -> None: ...

    def warning(self, msg: object, *args: object, **kwargs: object) -> None: ...


class Args(Protocol):
    """Minimal protocol for argparse/simple-namespace args used by CLI helpers."""

    yes: bool | int | None
    embed_cover_art: bool | None
    apply_metadata: bool | None
