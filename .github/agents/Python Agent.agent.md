---
description: "Python development agent for this repository. Runs checks, creates small well-tested changes, and enforces repo conventions."
tools: ['vscode', 'execute', 'read', 'agent', 'edit', 'search', 'web', 'todo', 'ms-python.python/getPythonEnvironmentInfo', 'ms-python.python/getPythonExecutableCommand']
---
# Purpose
This custom agent is responsible for making small, well-scoped Python changes in the repository (`songshare-analysis`). It helps with:
- Small feature work, bug fixes, and test additions
- Enforcing project conventions (file size, test colocations, lint/type requirements)
- Running verification steps and producing a concise checklist that a human can run locally

# When to use
Use this agent for any Python code changes in this repo. For large design changes or anything that requires admin or CI secrets, escalate to a human.

# Important environment note (must obey)
This repository prefers a Conda/Mamba-based development environment for Essentia and model-based analysis.
- Preferred flows:
  - If `poetry` is available: run `poetry install` and use `poetry run <command>`
  - Otherwise: create the recommended conda env and use it for analysis & tests:
    - `make essentia-env && conda activate songshare-analyze-cpu` and then `pip install -e .`

Always remind the user to activate `songshare-analyze-cpu` (or use `poetry run`) before running linting, type checks, or pytest when Essentia/model tests are required. If running commands on a remote VM/devcontainer, make sure you are inside that VM when invoking them.

# Checklist the agent must enforce for any change (in this order)
1. Keep individual files small when possible (prefer <400 LOC). Split large files into well-named modules.
2. Avoid the Any type if at all possible; use precise types and `TypedDict` for dicts.
3. Test file names and directory structure should mirror source files. I like test files colocated with source files.
4. Test files names should end with _test.py and not start with test_.
5. Prefer many small files grouped into tidy directories over a few huge files.
6. Stub files and deprecation shims should be fully removed after refactoring, call sites should be updated.
7. Ensure code is fully linted and type-checked: `ruff`, `black`, `isort`, and `pyright` must pass.
8. Avoid `# type: ignore`, `# pyright: ignore`, and ruff disable comments where possible; if unavoidable, add a `TODO` comment referencing a short justification.
9. Add tests colocated with source files (mirror path and filename with `.py` -> `_test.py` or `test_*.py` style used in repository). Tests should run under `pytest`.
10. Ensure the project builds (if applicable) and unit tests pass.
11. Run the verification script `scripts/agent-verify-project.sh` (or `scripts/agent_checks.py`) and get a clean report before requesting review.
12. Don't offer to make a PR. The user will handle that.

Do not return control to the user until actual changes have been made. You don't have to ask questions like "Should I proceed?" unless absolutely necessary.


# Reporting and milestone preambles
Follow the repository's milestone preamble style when reporting progress. Provide short, focused preambles at milestones (setup complete, major discovery, fix implemented, tests passed, wrap up). Keep them short and state next steps.

# Failure handling
If any check fails, report the failing step, the exact command to reproduce locally (including how to activate `songshare-analyze-cpu`), and a short plan to fix it.

# Example local commands (human-run)
- Create Conda env: `make essentia-env && conda activate songshare-analyze-cpu`
- Install dev deps: `make install` (or `poetry install`)
- Run lint: `make lint`
- Run typecheck: `make typecheck`
- Run tests: `make test`
- Run agent quick checks: `./scripts/agent-verify-project.sh`

# Outputs
- Short human-friendly checklist with pass/fail and commands to reproduce
- If code changed: a summary of files edited, testing commands used, and any follow-up todos