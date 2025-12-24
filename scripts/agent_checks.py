#!/usr/bin/env python3
"""Small static checks useful for the agent and humans.

This script intentionally avoids external dependencies so it can run inside
minimal environments (for example, a lightweight Python interpreter) and in
CI shells before dev dependencies are installed.

Checks performed:
- Long files (prefer <400 lines)
- Presence of `# type: ignore`, `# pyright: ignore`, or ruff disable comments
- Quick heuristic for tests present for source modules

Exit status: 0 if all checks pass, >0 otherwise.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"

LONG_FILE_THRESHOLD = 400
IGNORE_PATTERN = re.compile(
    r"#\s*type:\s*ignore|#\s*noqa|#\s*ruff:\s*noqa|#\s*pyright:\s*ignore"
)


def list_py_files(base: Path) -> Iterable[Path]:
    if not base.exists():
        return
    for p in base.rglob("*.py"):
        # skip generated caches
        if "__pycache__" in p.parts:
            continue
        yield p


def find_long_files(files: Iterable[Path], threshold: int) -> List[Tuple[Path, int]]:
    out: List[Tuple[Path, int]] = []
    for p in files:
        try:
            n = sum(1 for _ in p.open("r", encoding="utf8", errors="ignore"))
        except OSError:
            continue
        if n > threshold:
            out.append((p, n))
    return out


def find_ignored_types(files: Iterable[Path]) -> List[Tuple[Path, int, List[str]]]:
    out: List[Tuple[Path, int, List[str]]] = []
    for p in files:
        lines = p.read_text(encoding="utf8", errors="ignore").splitlines()
        matches: List[str] = []
        for i, line in enumerate(lines, start=1):
            if IGNORE_PATTERN.search(line):
                matches.append(f"{i}: {line.strip()}")
        if matches:
            out.append((p, len(matches), matches))
    return out


def has_test_for_module(module: Path, tests: Iterable[Path]) -> bool:
    name = module.stem
    # Accept tests that contain the module stem in filename
    for t in tests:
        if name in t.stem:
            return True
    return False


def find_uncovered_modules(
    src_files: Iterable[Path], test_files: Iterable[Path]
) -> List[Path]:
    test_files_list = list(test_files)
    uncovered: List[Path] = []
    for m in src_files:
        # skip package __init__ modules
        if m.stem == "__init__":
            continue
        if not has_test_for_module(m, test_files_list):
            uncovered.append(m)
    return uncovered


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=LONG_FILE_THRESHOLD)
    args = parser.parse_args(argv)

    src_files = list(list_py_files(SRC))
    test_files = list(list_py_files(TESTS))

    long_files = find_long_files(src_files + test_files, args.threshold)
    ignored = find_ignored_types(src_files + test_files)
    uncovered = find_uncovered_modules(src_files, test_files)

    ok = True

    if long_files:
        ok = False
        print(
            "\n⚠️ Long files (prefer < {threshold} LOC):".format(
                threshold=args.threshold
            )
        )
        for p, n in sorted(long_files, key=lambda x: -x[1]):
            print(f" - {p.relative_to(ROOT)}: {n} lines")

    if ignored:
        ok = False
        print("\n⚠️ Found type-ignore or noqa comments:")
        for p, count, matches in ignored:
            print(f" - {p.relative_to(ROOT)}: {count} occurrences")
            for m in matches[:5]:
                print(f"    {m}")

    if uncovered:
        ok = False
        print("\n⚠️ Potentially uncovered modules (no matching test filename):")
        for p in sorted(uncovered):
            print(f" - {p.relative_to(ROOT)}")

    if ok:
        print("✅ Agent quick checks passed.")
        return 0
    print(
        "\nPlease address the issues above. For full checks run inside a Conda/Mamba\n"
        "environment (recommended):\n"
        "  make essentia-env && conda activate songshare-analyze-cpu\n"
        "  pip install -e .\n"
        "  make lint && make typecheck && make test"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
