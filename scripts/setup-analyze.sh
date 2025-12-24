#!/usr/bin/env bash
set -euo pipefail

# Small helper script to create and activate the conda env for analyze-based analysis.
# Usage: ./scripts/setup-analyze.sh

if ! command -v conda >/dev/null 2>&1 && ! command -v mamba >/dev/null 2>&1; then
  echo "ERROR: conda or mamba is required to create the analyze environment."
  echo "Install Miniconda or Mambaforge: https://mamba.readthedocs.io/en/latest/"
  exit 1
fi

ENV_FILE="environment.analyze-cpu.yml"
ENV_NAME="songshare-analyze-cpu"

echo "Creating conda env from ${ENV_FILE} (name: ${ENV_NAME})..."

if command -v mamba >/dev/null 2>&1; then
  echo "Using mamba for fast environment creation"
  mamba env create -f "${ENV_FILE}" || echo "Environment exists or creation failed"
  MCONDA=mamba
else
  conda env create -f "${ENV_FILE}" || echo "Environment exists or creation failed"
  MCONDA=conda
fi

printf "\nTo activate the environment run:\n  conda activate %s\nThen install the project into it (editable):\n  # Install Poetry into the env and run: `poetry install`\n  mamba run -n %s pip install poetry && mamba run -n %s poetry install\n  # or: pip install -e .\n" "${ENV_NAME}" "${ENV_NAME}" "${ENV_NAME}"

# Ensure Poetry is installed inside the environment and run it there
if ${MCONDA} run -n "${ENV_NAME}" poetry --version >/dev/null 2>&1; then
  echo "Poetry found inside '${ENV_NAME}' — running 'poetry install' inside the env..."
  ${MCONDA} run -n "${ENV_NAME}" poetry install || echo "'poetry install' failed; please run it manually inside the env."
else
  echo "Poetry not found in '${ENV_NAME}' — installing Poetry into the environment and running install..."
  ${MCONDA} run -n "${ENV_NAME}" pip install poetry || echo "Failed to install Poetry into the env; please install it manually."
  ${MCONDA} run -n "${ENV_NAME}" poetry install || echo "'poetry install' failed; please run it manually inside the env."
fi
