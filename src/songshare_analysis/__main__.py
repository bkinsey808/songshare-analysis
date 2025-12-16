"""CLI entrypoint for songshare-analysis.

Provides a simple CLI using argparse. Uses logging instead of print for more
flexible output control and to be more idiomatic for real-world applications.
"""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

from .core import dataframe_summary, sample_dataframe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="songshare-analyze")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a small summary of plays instead of the full table",
    )
    parser.add_argument(
        "--csv", action="store_true", help="Output CSV instead of a table"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    parser = build_parser()
    args = parser.parse_args(argv)

    df = sample_dataframe()
    if args.summary:
        s = dataframe_summary(df)
        logger.info("Summary: %s", s)
        return

    if args.csv:
        # Print CSV to stdout; users can redirect as needed
        print(df.to_csv(index=False))
    else:
        # Fallback: pretty table; pandas.DataFrame.__str__ behaves well
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
