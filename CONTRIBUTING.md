Thank you for contributing! Please follow these guidelines:

- Use the `src/` layout in this repository.
- Run formatting and linting before opening a PR: `make format` and `make lint`.
- Write tests for new features or bug fixes.
- Update `CHANGELOG.md` (if present) with notable changes for new releases.

A good PR includes unit tests and a short description of the change.

Environment and Poetry usage note:
- **Do not install Poetry globally.** Instead, prefer installing and running Poetry inside the `songshare-analyze-cpu` conda environment or a dedicated virtualenv. This prevents global tool conflicts and ensures `poetry install` uses the correct interpreter and native binaries (Essentia, PyTorch). For example:

```bash
# create and activate the conda env
make essentia-env
conda activate songshare-analyze-cpu
# install Poetry in the env and run it there
pip install poetry
poetry install
```

Requirements files (when to update)
- `requirements.txt` and `requirements-dev.txt` are convenience pip manifests and should be updated **on-demand** for Docker images or pip-only CI.
- To generate/update them:
  - From Poetry (authoritative for Python deps):

```bash
poetry export -f requirements.txt --without-hashes -o requirements.txt
```

  - From the running conda env (captures exact installed pip packages):

```bash
mamba run -n songshare-analyze-cpu pip freeze > requirements-analyze.txt
```

- Commit generated requirements files only when you intend them to be consumed by downstream tooling (Docker images, pip-only CI), and document their origin in the commit message.
