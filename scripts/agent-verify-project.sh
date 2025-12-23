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

if [ -f .venv/bin/activate ]; then
  echo ".venv detected. Activating and running checks"
  # shellcheck disable=SC1091
  . .venv/bin/activate
  ruff check .
  isort --check-only .
  black --check .
  pyright src/
  pytest -q
  echo "All checks passed in .venv"
  exit 0
fi

cat <<'EOF'
Could not run checks automatically because no venv or poetry is available.
Please run these steps locally:

  # create venv and activate
  make venv && source .venv/bin/activate
  # install dev deps
  make install
  # run checks
  make lint
  make typecheck
  make test

You can run quick static checks without installing deps:
  python scripts/agent_checks.py

EOF
exit 2
