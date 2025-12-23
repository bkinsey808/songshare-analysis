#!/usr/bin/env bash
set -euo pipefail

# Small helper script to create and activate the conda env for Essentia-based analysis.
# Usage: ./scripts/setup-essentia.sh

if ! command -v conda >/dev/null 2>&1 && ! command -v mamba >/dev/null 2>&1; then
  echo "ERROR: conda or mamba is required to create the Essentia environment."
  echo "Install Miniconda or Mambaforge: https://mamba.readthedocs.io/en/latest/"
  exit 1
fi

ENV_FILE="environment.essentia.yml"
ENV_NAME="songshare-essentia"

echo "Creating conda env from ${ENV_FILE} (name: ${ENV_NAME})..."

if command -v mamba >/dev/null 2>&1; then
  echo "Using mamba for fast environment creation"
  mamba env create -f "${ENV_FILE}" || echo "Environment exists or creation failed"
else
  conda env create -f "${ENV_FILE}" || echo "Environment exists or creation failed"
fi

printf "\nTo activate the environment run:\n  conda activate %s\nThen install the project into it (editable):\n  poetry install\n  # or: pip install -e .\n" "${ENV_NAME}"

# If poetry is available, offer to install the project automatically into the env
if command -v poetry >/dev/null 2>&1; then
  echo "Poetry detected — installing project into the activated environment..."
  # Use the env's Python by invoking poetry in a subshell with the conda env activated
  # Note: user may still prefer to run `poetry install` manually.
  (
    set -euo pipefail
    conda activate "${ENV_NAME}"
    poetry install
  ) || echo "Automatic 'poetry install' failed; please run 'poetry install' manually inside the env."
else
  echo "No Poetry detected. Run 'poetry install' inside the activated env to install the project."
fi
