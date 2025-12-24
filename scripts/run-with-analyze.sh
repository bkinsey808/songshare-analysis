#!/usr/bin/env bash
set -euo pipefail

# Helper to run songshare-analyze id3 --analyze inside the `songshare-analyze-cpu`
# conda environment. Detects mamba/conda and performs an editable install of the
# project inside the env (if not already present).
# Usage: ./scripts/run-with-analyze.sh /full/path/to/file.mp3

if [ $# -ne 1 ]; then
  echo "Usage: $0 /full/path/to/file.mp3"
  exit 2
fi
FILE="$1"

if command -v mamba >/dev/null 2>&1; then
  MCONDA=mamba
elif command -v conda >/dev/null 2>&1; then
  MCONDA=conda
else
  echo "mamba or conda is required to run this script" >&2
  exit 1
fi

# Ensure project is installed in the env (editable install); ignore install
# errors (package may already be present).
${MCONDA} run -n songshare-analyze-cpu bash -lc "cd \"$(pwd)\" && pip install -e . >/dev/null 2>&1 || true"
# Run the CLI in the env
${MCONDA} run -n songshare-analyze-cpu bash -lc "songshare-analyze id3 \"${FILE}\" --analyze"
