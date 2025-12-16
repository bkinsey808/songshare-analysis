"""Core functions for the Songshare analysis package.

This module provides a small example: generating a sample `pandas.DataFrame`.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def sample_dataframe() -> pd.DataFrame:
    """Return a tiny sample dataframe that demonstrates a function for tests.

    This function is intentionally simple but shows how to annotate the return
    type. When your codebase grows, prefer `TypedDict` or dataclasses for rows
    that need strong typing.
    """
    return pd.DataFrame({"song": ["A", "B"], "plays": [10, 20]})


def dataframe_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Return a small summary of the dataframe's plays.

    This demonstrates accepting a typed parameter and returning a typed dict.
    """
    total_plays = df["plays"].sum()
    return {"rows": len(df), "total_plays": int(total_plays)}
