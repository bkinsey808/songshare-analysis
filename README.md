# songshare-analysis

A small, well-structured Python project scaffold for the Songshare analysis codebase.

This repository includes a `src/` style Python package layout, minimal example code, tests, and recommended developer tooling.

Quick start
-----------

Environments & dependency workflow
----------------------------------

This project uses a hybrid approach to manage dependencies and native binaries:

- **Conda / Mamba (`environment.analyze-cpu.yml`)**: the *canonical* environment file for native binaries (Essentia, ffmpeg, CPU-specific PyTorch wheel). Use `mamba` where possible for speed.
- **Poetry (`pyproject.toml`)**: the canonical Python package manifest for the project (extras, entry points, packaging). Run `poetry install` *inside* the conda env so Poetry uses that interpreter and has access to native libraries.
- **requirements.txt / requirements-dev.txt**: convenience pip-style files for Docker or pip-only workflows (treat these as *generated* artifacts; update them via Poetry export or `pip freeze` when needed).

Typical setup (recommended):

```bash
# create/update the conda env (mamba preferred)
make songshare-analyze-cpu (creates 'songshare-analyze-cpu')
conda activate songshare-analyze-cpu
# ensure Poetry is installed inside the env and run it there
pip install poetry
poetry install
```

If you prefer an all-in-one scripted flow (no activation):

```bash
# Setup script installs Poetry inside the env and runs 'poetry install' there
./scripts/setup-analyze.sh
```

Generating pip requirements (optional):

- From Poetry (authoritative for Python deps):
  ```bash
  poetry export -f requirements.txt --without-hashes -o requirements.txt
  ```

- From the installed environment (captures actual pip-installed packages):
  ```bash
  mamba run -n songshare-analyze-cpu pip freeze > requirements-analyze.txt
  ```

CI guidance:

- Use `conda-incubator/setup-miniconda` or `mamba` and the `environment.analyze-cpu.yml` file for Essentia-enabled tests.
- Run `poetry install` inside that environment (e.g., `mamba run -n songshare-analyze-cpu poetry install`) rather than installing Poetry globally on runners.


**Note:** For Essentia and model-based analysis (PANNs) the recommended workflow is
to use the `songshare-analyze-cpu` conda/mamba environment (see
`docs/essentia-integration.md`). This environment contains native binaries and
platform-specific wheels that avoid long native builds and ensures `--analyze`
works reliably.

Create a Python virtual environment and install dependencies with Poetry (recommended). For Essentia/model work use the conda env and run Poetry inside that env:

```bash
# Create and activate the conda env (mamba preferred)
# make songshare-analyze-cpu   # alias: make essentia-env
conda activate songshare-analyze-cpu
# Install Poetry into the activated env if needed and run it there
pip install poetry
poetry install
# Or, without activating: mamba run -n songshare-analyze-cpu pip install poetry && mamba run -n songshare-analyze-cpu poetry install
```

If you prefer to use Conda/Mamba (recommended for Essentia and model-based analysis):

```bash
# Create the analyze-enabled conda env (mamba preferred).
make songshare-analyze-cpu
conda activate songshare-analyze-cpu
pip install -e .
```

Model (PANNs) note: `panns-inference` is included in the `environment.analyze-cpu.yml` environment for semantic tagging. On first use a model checkpoint (~300MB) will be downloaded to `~/panns_data/` and PANNs will run on CPU by default (we prefer the CPU-only PyTorch wheel in this project to avoid GPU deps).

If you don't need Essentia native binaries and prefer Poetry for a lighter workflow, run `poetry install` from within a controlled Python environment (e.g., inside a Conda env or a virtualenv). Avoid installing Poetry globally — instead install Poetry into the chosen environment (for example: `mamba run -n songshare-analyze-cpu pip install poetry && mamba run -n songshare-analyze-cpu poetry install`).

VS Code interpreter & pytest imports
----------------------------------

If you see warnings like "Import 'pytest' could not be resolved" in VS Code (Pylance), it usually means the editor isn't using the project virtual environment.

To fix this on a Poetry-managed project:

```bash
# Install dependencies via Poetry
poetry install

# In VS Code: Command Palette -> Python: Select Interpreter -> choose the interpreter
# associated with the environment you use (e.g., 'songshare-analyze-cpu' or a Poetry-managed environment)
```

For Windows the path will point to the selected interpreter's Scripts dir (e.g., `C:\path\to\songshare-analyze-cpu\Scripts\python.exe`).

If you use the `songshare-analyze-cpu` conda env, select that interpreter in VS Code to ensure Essentia and model packages are resolved correctly.

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
code --install-extension njpwerner.autodocstring
code --install-extension GitHub.vscode-pull-request-github
```

Workspace/interpreter selection
--------------------------------
This repository recommends selecting the Conda/Mamba `songshare-analyze-cpu` environment in your editor when working with Essentia or model-based features. Alternatively, you can continue to use Poetry-managed environments for lighter workflows.

To set the interpreter in VS Code:

```bash
# If using Conda/Mamba
conda activate songshare-analyze-cpu
# In VS Code: Command Palette -> Python: Select Interpreter -> choose the 'songshare-analyze-cpu' interpreter

# If using Poetry-managed environments
poetry config virtualenvs.in-project true
poetry install
```

Selecting the appropriate interpreter ensures Pylance/pyright and pytest resolve packages correctly.


Exporting requirements
----------------------

If you need `requirements.txt` for Docker or another toolchain, export from the Poetry-managed configuration with:

```bash
poetry export -f requirements.txt --without-hashes -o requirements.txt
poetry export -f requirements.txt --dev --without-hashes -o requirements-dev.txt
```

Run tests:

```bash
# With Poetry
poetry run pytest

# Or inside the 'songshare-analyze-cpu' conda env
# conda activate songshare-analyze-cpu && pytest
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
