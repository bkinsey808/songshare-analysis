#!/usr/bin/env bash
set -euo pipefail

# Convenience script to install Mambaforge (if missing), create the analyze conda
# environment, and run the analyze-specific tests.
# Usage: ./scripts/run-analyze-tests.sh [--no-install] [pytest-args]

NO_INSTALL=0
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-install)
      NO_INSTALL=1
      shift
      ;;
    --)
      shift
      PYTEST_ARGS+=("$@")
      break
      ;;
    *)
      PYTEST_ARGS+=("$1")
      shift
      ;;
  esac
done

if ! command -v mamba >/dev/null 2>&1 && ! command -v conda >/dev/null 2>&1; then
  if [ "$NO_INSTALL" -eq 1 ]; then
    echo "ERROR: conda/mamba not found and --no-install given. Aborting."
    exit 1
  fi
  echo "conda/mamba not found — installing Mambaforge (user-local)..."
  ./scripts/install-mambaforge.sh
  echo "Please restart your shell or add the mambaforge bin directory to PATH before re-running this script."
  echo "If you are running in CI, the action will automatically install and use mamba for you."
  exit 0
fi

# Create or update the environment
echo "Creating/updating 'songshare-analyze-cpu' conda environment..."
if command -v mamba >/dev/null 2>&1; then
  mamba env create -f environment.analyze-cpu.yml || mamba env update -f environment.analyze-cpu.yml -n songshare-analyze-cpu --prune
else
  conda env create -f environment.analyze-cpu.yml || conda env update -f environment.analyze-cpu.yml -n songshare-analyze-cpu --prune
fi

# Run tests
echo "Running analyze tests in 'songshare-analyze-cpu'..."
if command -v mamba >/dev/null 2>&1; then
  mamba run -n songshare-analyze-cpu pytest "${PYTEST_ARGS[@]:-src/songshare_analysis/test_essentia_mp3.py -q}"
else
  conda run -n songshare-analyze-cpu pytest "${PYTEST_ARGS[@]:-src/songshare_analysis/test_essentia_mp3.py -q}"
fi
