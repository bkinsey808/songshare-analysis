#!/usr/bin/env bash
set -euo pipefail

# Quick wrapper to run the project's checks. This script tries to run the
# canonical `make` or `poetry run` commands but will not attempt to install
# dependencies. If dependencies are missing, it will print instructions.

echo "Agent: running quick verification checks"

if command -v poetry >/dev/null 2>&1; then
  echo "Using poetry (poetry run ...). Running lint, typecheck, and tests"
  poetry run ruff check .
  poetry run isort --check-only .
  poetry run black --check .
  poetry run pyright src/
  poetry run pytest -q
  echo "All checks passed under poetry"
  exit 0
fi

# Prefer running inside the 'songshare-analyze-cpu' conda env if present
if command -v mamba >/dev/null 2>&1 && mamba env list | grep -q "songshare-analyze-cpu" 2>/dev/null; then
  echo "Found 'songshare-analyze-cpu' env. Running checks inside it"
  mamba run -n songshare-analyze-cpu ruff check .
  mamba run -n songshare-analyze-cpu isort --check-only .
  mamba run -n songshare-analyze-cpu black --check .
  mamba run -n songshare-analyze-cpu pyright src/
  mamba run -n songshare-analyze-cpu pytest -q
  echo "All checks passed in 'songshare-analyze-cpu'"
  exit 0
fi

if command -v conda >/dev/null 2>&1 && conda env list | grep -q "songshare-analyze-cpu" 2>/dev/null; then
  echo "Found 'songshare-analyze-cpu' env. Running checks inside it"
  conda run -n songshare-analyze-cpu ruff check .
  conda run -n songshare-analyze-cpu isort --check-only .
  conda run -n songshare-analyze-cpu black --check .
  conda run -n songshare-analyze-cpu pyright src/
  conda run -n songshare-analyze-cpu pytest -q
  echo "All checks passed in 'songshare-analyze-cpu'"
  exit 0
fi

cat <<'EOF'
Could not run checks automatically because neither Poetry nor the 'songshare-analyze-cpu' Conda env was found.
Please run these steps locally:

  # create the esssential env
  make essentia-env
  conda activate songshare-analyze-cpu
  # install dev deps into that env
  pip install -e .
  # run checks
  make lint
  make typecheck
  make test

You can run quick static checks without installing deps:
  python scripts/agent_checks.py

EOF
exit 2
