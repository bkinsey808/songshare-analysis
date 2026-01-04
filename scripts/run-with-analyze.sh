#!/usr/bin/env bash
set -euo pipefail

# Helper to run songshare-analyze id3 --analyze inside the `songshare-analyze-cpu`
# conda environment. Detects mamba/conda and performs an editable install of the
# project inside the env (if not already present).
# Usage: ./scripts/run-with-analyze.sh /full/path/to/file.mp3|/full/path/to/dir [-r|--recursive]

usage() {
  echo "Usage: $0 /full/path/to/file.mp3|/full/path/to/dir [-r|--recursive] [-e|--ensure-deps]"
  exit 2
}

if [ $# -lt 1 ] || [ $# -gt 3 ]; then
  usage
fi

# Parse args: first non-flag is treated as FILE; flags: -r/--recursive, -e/--ensure-deps
FILE=""
RECURSIVE_FLAG=""
ENSURE_DEPS=0
for ARG in "$@"; do
  case "$ARG" in
    -r|--recursive)
      RECURSIVE_FLAG="-r"
      ;;
    -e|--ensure-deps)
      ENSURE_DEPS=1
      ;;
    -* )
      echo "Unknown option: $ARG" >&2
      usage
      ;;
    *)
      if [ -z "$FILE" ]; then
        FILE="$ARG"
      else
        echo "Extra argument: $ARG" >&2
        usage
      fi
      ;;
  esac
done

if [ -z "$FILE" ]; then
  usage
fi

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

# Optionally ensure runtime deps and extras are installed in the env
if [ "$ENSURE_DEPS" -eq 1 ]; then
  echo "Ensuring runtime dependencies and analysis extras are installed in the env..."
  ${MCONDA} run -n songshare-analyze-cpu bash -lc "cd \"$(pwd)\" && pip install -r requirements.txt >/dev/null 2>&1 || true"
  # Install optional extras for Essentia and model-based analysis
  ${MCONDA} run -n songshare-analyze-cpu bash -lc "cd \"$(pwd)\" && pip install -e '.[essentia,panns]' >/dev/null 2>&1 || true"
fi

# Run the CLI in the env
${MCONDA} run -n songshare-analyze-cpu bash -lc "songshare-analyze id3 \"${FILE}\" --analyze ${RECURSIVE_FLAG}"
