# songshare-analysis

A small, well-structured Python project scaffold for the Songshare analysis codebase.

This repository includes a `src/` style Python package layout, minimal example code, tests, and recommended developer tooling.

Quick start
-----------

Create a Python virtual environment and install dependencies with Poetry (recommended):

```bash
# Install poetry: https://python-poetry.org/docs/
curl -sSL https://install.python-poetry.org | python3 -
poetry install
```

If you don’t want to use Poetry, you can fall back to virtualenv + pip (not recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

VS Code interpreter & pytest imports
----------------------------------

If you see warnings like "Import 'pytest' could not be resolved" in VS Code (Pylance), it usually means the editor isn't using the project virtual environment.

To fix this on a Poetry-managed project:

```bash
# Configure Poetry to create in-project virtualenvs
poetry config virtualenvs.in-project true
poetry install

# In VS Code: Command Palette -> Python: Select Interpreter -> choose .venv/bin/python
```

For Windows the path is `.venv\Scripts\python.exe`.

If you prefer not to make the venv in-project you can still select the right Poetry venv via the VS Code interpreter selector.

If you still see unresolved imports in the editor after selecting the correct interpreter:

- Restart VS Code so Pylance picks up the environment packages.
- Run `poetry run python -m pip list` to ensure `pytest` and other dev dependencies are installed.
- Ensure `.vscode/settings.json` does not hard-code a wrong `python.defaultInterpreterPath` (we removed that for portability; prefer local selection).

VS Code recommended extensions
------------------------------

This project recommends the following VS Code extensions to provide a smooth developer experience:

- `ms-python.python` (Python extension)
- `ms-python.vscode-pylance` (Pylance language server)
- `charliermarsh.ruff` (Ruff linter)
- `ms-python.black-formatter` (Black formatter)
- `ms-python.isort` (isort import sorting)
- `njpwerner.autodocstring` (docstring generation)
- `GitHub.vscode-pull-request-github` (optional: GitHub PR support)

To install them automatically using the VS Code CLI (if available) run:

```bash
scripts/install-vscode-extensions.sh
```

Or install them manually:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
code --install-extension ms-python.black-formatter
code --install-extension ms-python.isort
code --install-extension ms-python.mypy-type-checker
code --install-extension njpwerner.autodocstring
code --install-extension GitHub.vscode-pull-request-github
```

Workspace-enforced interpreter (optional)
---------------------------------------
This repository enforces the workspace Python interpreter to an in-project virtualenv `.venv`. If you prefer to follow that workflow:

```bash
poetry config virtualenvs.in-project true
poetry install
```

Then open VS Code and choose the `.venv/bin/python` interpreter or use the emulator settings; the workspace will default to the in-project interpreter automatically.


Exporting requirements
----------------------

If you need `requirements.txt` for Docker or another toolchain, export from the Poetry-managed configuration with:

```bash
poetry export -f requirements.txt --without-hashes -o requirements.txt
poetry export -f requirements.txt --dev --without-hashes -o requirements-dev.txt
```

Run tests:

```bash
poetry run pytest
# or with a venv
# . .venv/bin/activate && pytest
```

Pre-commit hooks
----------------
Export requirements for alternative workflows
--------------------------------------------

If you use Docker or a non-Poetry workflow that needs a `requirements.txt`, you can export one from Poetry:

```bash
poetry export -f requirements.txt --without-hashes -o requirements.txt
poetry export -f requirements.txt --dev --without-hashes -o requirements-dev.txt
```

Install the git hooks locally with:

```bash
pip install pre-commit
pre-commit install
```

This installs hooks so that Black, ruff, and isort run before commits.

Optional Node-based commit tooling (Husky / Commitlint / Commitizen)

If you prefer to use the same commit linting and hook tooling used in other SongShare repos, you can add a minimal Node setup to enable Husky hooks and Commitlint:

```bash
# 1. Install dependencies (run in repo root)
npm install --save-dev husky @commitlint/cli @commitlint/config-conventional commitizen cz-conventional-changelog lint-staged

# 2. Activate husky (creates .husky/_/husky.sh)
# Ensure Node and npm are installed first and run `npm install` before `npm run prepare`.
# If `npm run prepare` fails, try `npx husky install` which also creates the necessary hooks.
npm run prepare

# 3. Use `npm run commit` (Commitizen) to create conventional commits or continue using `git commit`.
#    Husky will run `commitlint` on commit message and `lint-staged` on staged files when configured.
```

Note: The repo contains a `package.json`, `commitlint.config.js`, `lint-staged.config.mjs`, and `.husky/` hooks to mirror the setup from `songshare-effect`. If you don't plan to use Node-based hooks, you can ignore these files.

CLI
---

If you install the package as editable, you can run the CLI with:

```bash
pip install -e .
songshare-analyze --summary
songshare-analyze --csv > output.csv
```

The CLI supports the following options:

- `--summary`: print a small JSON-like summary of the dataset
- `--csv`: print a CSV of the sample dataset to stdout

Typing
------

This project uses `pyright` (via `pyrightconfig.json`) for editor type checking and `ruff`/`black` for linting and formatting.

Install dev deps and run the editor typecheck tool:

```bash
pip install -r requirements-dev.txt
# Use your editor's Pyright/Pylance integration or run:
pyright
```

Notes about pandas and typing:

- Pandas is dynamically typed; we include `pandas-stubs` in `requirements-dev.txt` to help with `pyright` and static analysis.

Strict type checking
--------------------

This repo runs `pyright` as part of local checks and CI where appropriate. Use the Makefile `typecheck` target to run the type checker locally:

```bash
make typecheck
```

If you need to temporarily suppress checks for a file, add `# type: ignore` with a corresponding `TODO` note to track technical debt.

Format & lint:

```bash
black .
ruff .
```

Formatting & Linting guidance
---------------------------

- We use `Black` for formatting, `isort` for imports, and `ruff` for linting (flake8-like checks and some fixes).
- `Ruff` is fast and can automatically fix many lint issues (it’s configured to auto-fix in `pre-commit`) and also provides `ruff format`/`ruff check --fix` to automatically fix errors.
- To format and lint everything locally, run:

```bash
make format
make lint
```

- To enable git hooks that auto-format and lint staged files, install and enable pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # to apply hooks across the repo now
```

Ruff & Black integration
------------------------
- `isort` follows the Black import style via `profile = "black"` in `pyproject.toml`.
- We run `isort` first, then `black`, then `ruff` auto-fix; this ordering prevents reformatting conflicts and keeps CI checks deterministic.
