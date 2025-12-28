#!/usr/bin/env bash
set -euo pipefail

# Wrapper to create the recommended `songshare-analyze-cpu` Conda environment.
# Prefer using `mamba` when available for faster installs.
if command -v mamba >/dev/null 2>&1 || command -v conda >/dev/null 2>&1; then
  echo "Creating or updating 'songshare-analyze-cpu' environment..."
  make analyze-env   # alias: make essentia-env
  echo "Activate it with: conda activate songshare-analyze-cpu"
  echo "Then install the project (editable) inside that env: pip install -e ."
else
  echo "Conda or mamba not found. Install Mambaforge/Conda and re-run this script or use Poetry." >&2
  exit 1
fi

echo "Created/updated 'songshare-analyze-cpu'. Activate it with: conda activate songshare-analyze-cpu and then run: pip install -e ."