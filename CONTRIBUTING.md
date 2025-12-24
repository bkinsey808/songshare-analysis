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

