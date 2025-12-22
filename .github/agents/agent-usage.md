## Python Agent — usage notes

This repository includes a small custom agent definition (`Python Agent.agent.md`) and quick verification scripts under `scripts/`.

Key commands (run inside the project's venv or with `poetry run`):

- Quick static checks (no deps required):
  - python scripts/agent_checks.py

- Full checks (requires dev deps):
  - make venv && source .venv/bin/activate
  - make install
  - make lint
  - make typecheck
  - make test

Or use the convenience wrapper (if you have `poetry` or a `.venv`):

- ./scripts/agent-verify-project.sh

Reminder: many commands only work when executed inside the VM or with the project's venv activated. If you run into missing commands such as `pytest` or `mypy`, activate the venv and install dev dependencies first (via `make install` or `poetry install`).
