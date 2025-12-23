#!/usr/bin/env bash
set -euo pipefail

# Convenience script to install Mambaforge (if missing), create the Essentia conda
# environment, and run the Essentia-specific tests.
# Usage: ./scripts/run-essentia-tests.sh [--no-install] [pytest-args]

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

# Create or update the Essentia environment
echo "Creating/updating 'songshare-essentia' conda environment..."
if command -v mamba >/dev/null 2>&1; then
  mamba env create -f environment.essentia.yml || mamba env update -f environment.essentia.yml -n songshare-essentia --prune
else
  conda env create -f environment.essentia.yml || conda env update -f environment.essentia.yml -n songshare-essentia --prune
fi

# Run tests
echo "Running Essentia tests in 'songshare-essentia'..."
if command -v mamba >/dev/null 2>&1; then
  mamba run -n songshare-essentia pytest "${PYTEST_ARGS[@]:-src/songshare_analysis/test_essentia_mp3.py -q}"
else
  conda run -n songshare-essentia pytest "${PYTEST_ARGS[@]:-src/songshare_analysis/test_essentia_mp3.py -q}"
fi
