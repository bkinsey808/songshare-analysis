from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover - external availability
    jsonschema = None


def _schema_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "docs" / "schemas" / "essentia-analysis.schema.json"


def test_schema_file_exists():
    p = _schema_path()
    assert (
        p.exists()
    ), "Schema file must exist: docs/schemas/essentia-analysis.schema.json"


def test_valid_and_invalid_examples():
    if jsonschema is None:
        pytest.skip("jsonschema not installed; install dev deps to run schema tests")

    p = _schema_path()
    schema = json.loads(p.read_text(encoding="utf8"))

    valid = {
        "version": "0.1",
        "provenance": {"tool": "essentia", "version": "2.1"},
        "analysis": {
            "rhythm": {"bpm": 120.0, "beats": [0.0, 0.5], "beat_cv": 0.01},
            "spectral": {"centroid": 3400.1},
        },
    }

    # should not raise
    jsonschema.validate(instance=valid, schema=schema)

    invalid = {"version": "0.1", "analysis": {"rhythm": {"bpm": "120"}}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)
