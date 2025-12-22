"""CLI entrypoint for songshare-analysis.

Provides a simple CLI using argparse. Uses logging instead of print for more
flexible output control and to be more idiomatic for real-world applications.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from typing import cast

from songshare_analysis.core import dataframe_summary, sample_dataframe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="songshare-analyze")
    subparsers = parser.add_subparsers(dest="command")

    # Existing top-level convenience flags (keep for backward compat)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a small summary of plays instead of the full table",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output CSV instead of a table",
    )

    # id3 subcommand: read tags from a file and print them
    id3_parser = subparsers.add_parser(
        "id3",
        help="Read ID3 tags from a file or directory",
    )
    id3_parser.add_argument(
        "path",
        help="Path to an audio file or a directory to scan",
    )
    id3_parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively scan directories for audio files",
    )
    id3_parser.add_argument(
        "--fetch-metadata",
        action="store_true",
        help=(
            "Fetch metadata from MusicBrainz based on tags (requires musicbrainzngs)"
        ),
    )
    id3_parser.add_argument(
        "--mb-fetch-missing",
        action="store_true",
        help=(
            "Only fetch MusicBrainz metadata when any core tag is missing"
            " (TIT2, TPE1, TALB) or MusicBrainz IDs are not present"
        ),
    )
    id3_parser.add_argument(
        "--apply-metadata",
        action="store_true",
        help=(
            "Apply fetched metadata to the file (preview by default; "
            "requires --yes to skip confirmation)"
        ),
    )
    id3_parser.add_argument(
        "--yes",
        action="store_true",
        help="When used with --apply-metadata, apply changes without prompting",
    )
    id3_parser.add_argument(
        "--embed-cover-art",
        action="store_true",
        help=(
            "When applying metadata, download and embed cover art if "
            "available and missing"
        ),
    )
    id3_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output for debugging and interactive inspection",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    # Default to quiet mode; enable INFO with --verbose
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger(__name__)

    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "verbose", False):
        logger.setLevel(logging.INFO)
        # Also set root level so library logs are visible when verbose
        logging.getLogger().setLevel(logging.INFO)

    df = sample_dataframe()
    if args.summary:
        s = dataframe_summary(df)
        logger.info("Summary: %s", s)
        return

    # Handle subcommands
    if args.command == "id3":
        from .id3_cli_process import ProcessArgs, handle_id3_command

        # Cast the parsed Namespace to the typed ProcessArgs protocol so the
        # static type checker recognizes the expected attributes.
        handle_id3_command(cast("ProcessArgs", args), logger)
        return

    if args.csv:
        # Print CSV to stdout; users can redirect as needed
        print(df.to_csv(index=False))
    else:
        # Fallback: pretty table; pandas.DataFrame.__str__ behaves well
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
