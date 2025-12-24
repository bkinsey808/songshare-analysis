from __future__ import annotations

import os
from pathlib import Path

import pytest

from songshare_analysis.essentia import (  # noqa: F401 - ensures package import
    essentia_extractor as ee,
)


@pytest.mark.essentia
def test_extract_tonal_basic():
    pytest.importorskip("essentia.standard")

    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_data")
    )
    candidate = os.path.join(base, "essentia_fixture.mp3")

    d = ee.extract_tonal(Path(candidate))

    assert isinstance(d, dict)
    assert "tonal" in d
    assert "chroma" in d
    assert "mfcc" in d


@pytest.mark.essentia
def test_extract_sections_basic():
    pytest.importorskip("essentia.standard")

    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_data")
    )
    candidate = os.path.join(base, "essentia_fixture.mp3")

    d = ee.extract_sections(Path(candidate))
    assert isinstance(d, dict)
    assert isinstance(d.get("sections"), list)
    assert all("start" in s and "end" in s for s in d.get("sections", []))


@pytest.mark.essentia
def test_extract_vocals_basic():
    pytest.importorskip("essentia.standard")

    base = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_data")
    )
    candidate = os.path.join(base, "essentia_fixture.mp3")

    d = ee.extract_vocals(Path(candidate))
    assert isinstance(d, dict)
    assert "vocals" in d
    assert isinstance(d["vocals"], dict)
