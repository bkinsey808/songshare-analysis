# Essentia Integration Plan ✅

## Overview

This document defines how to integrate Essentia into SongShare Analysis as an **optional feature extraction backend** for rhythm, tonal, and spectral analysis. It summarizes integration architecture, installation options, API design, ID3 -> JSON mapping rules, testing strategy, CI considerations, and a short implementation checklist.

---

## Goals 🎯

- Provide robust extraction of: **bpm, beats, onsets, mfccs, chroma, key, pitch, loudness, sections**, and other spectral features using Essentia.
- Store dense/per-frame outputs in a JSON sidecar and expose compact summaries to ID3/TXXX fields with conservative write rules.
- Keep Essentia optional (non-blocking for users who do not want heavy native deps).
- Provide clear provenance, confidence metrics, and reversible operations (dry-run, backups).

---

## Install & CI recommendations 🔧

- Preferred local installs:
  - Conda / Mamba (recommended): use the provided `environment.analyze-cpu.yml` for a reproducible environment (see below)
  - Pip (if compatible wheel exists): `pip install essentia` (verify platform wheel availability)
- CI options (non-Docker):
  - Provision the conda/mamba environment in CI using `conda-incubator/setup-miniconda` or `mamba` and the `environment.analyze-cpu.yml` file (see CI snippet below).
  - Alternatively run a separate workflow that uses a VM with Essentia preinstalled.
- Note: Essentia can be heavy to compile; keep it **optional** and avoid forcing it into main CI matrix. Use a small test fixture and a separate Essentia-enabled CI job to run full-feature tests.

**Model/semantic note (PANNs)**: This repository includes `panns-inference` in `environment.analyze-cpu.yml` for model-based semantic tagging (genre/mood/instruments). The first time you run a PANNs-based inference, the package will download a model checkpoint (~300MB) to `~/panns_data/` and use CPU execution by default. We recommend the CPU-only PyTorch wheel (already used in our environment) to avoid GPU dependencies in CI and developer machines.

### Conda env file

We include a ready-to-use `environment.analyze-cpu.yml` at the repo root. It prefers `essentia` from `conda-forge` but also provides a pip fallback when a conda package is not available for your platform (in our testing the `conda-forge` wheel was unavailable on some `ubuntu-latest` runners). If the conda package is unavailable the environment will install Essentia via `pip` as a fallback; prefer conda when possible to avoid long native builds. Example usage (mamba recommended):

```bash
# create the env (mamba preferred)
mamba env create -f environment.analyze-cpu.yml
# or with conda
conda env create -f environment.analyze-cpu.yml
```

Environment + Poetry workflow

- Purpose: allow native binaries (Essentia, CPU PyTorch) to be installed by conda while using Poetry for Python packaging and dependency declaration.
- Recommended flow (two-step):
  1. Create and activate the `songshare-analyze-cpu` conda env (see above).
  2. Install Poetry into that activated env and run `poetry install` there so Poetry uses the env's interpreter and native libs:

```bash
# inside an activated env
pip install poetry
poetry install
```

- One-step scripted alternative (no activation):
  - `./scripts/setup-analyze.sh` will create the env (via mamba/conda), install Poetry into the env if missing, and run `poetry install` inside the env.

Generating pip-style requirements (when needed)

- Use `poetry export` when you need a reproducible `requirements.txt` derived from the Poetry manifest:

```bash
poetry export -f requirements.txt --without-hashes -o requirements.txt
```

- Use `pip freeze` from the running env to capture exact installed packages (useful for Docker images):

```bash
mamba run -n songshare-analyze-cpu pip freeze > requirements-analyze.txt
```

CI recommendation

- In CI, prefer setting up the conda env and running Poetry inside it rather than installing Poetry globally: e.g.,

```yaml
- uses: conda-incubator/setup-miniconda@v2
  with:
    environment-file: environment.analyze-cpu.yml
    activate-environment: songshare-analyze-cpu
- name: Install project dependencies with Poetry inside env
  run: mamba run -n songshare-analyze-cpu pip install poetry && mamba run -n songshare-analyze-cpu poetry install
- name: Run tests
  run: mamba run -n songshare-analyze-cpu pytest -q
```

This avoids global Poetry installs on runners and keeps the job self-contained and reproducible. 
```bash
# create the env
mamba env create -f environment.analyze-cpu.yml
# or with conda
conda env create -f environment.analyze-cpu.yml

# activate
conda activate songshare-analyze-cpu

# install the project into the env (editable)
poetry install
# or: pip install -e .

# verify
python -c "import essentia; print('essentia', essentia.__version__)"
```

We also provide `scripts/setup-analyze.sh` as a small helper to create the env and show activation instructions.

Installing Mamba (Mambaforge)

If you don't have `mamba` installed locally we provide a helper to install Mambaforge in your user directory:

```bash
# Run the user-local Mambaforge installer (no sudo required)
./scripts/install-mambaforge.sh
# Then add the bin dir to your PATH (or restart your shell):
export PATH="$HOME/mambaforge/bin:$PATH"
```

Makefile convenience targets

- `make install-mamba` — downloads and installs Mambaforge (user-local) using the helper script.
- `make essentia-env` — creates or updates the `songshare-analyze-cpu` conda env using mamba (or conda) and prints instructions to activate it.
- `make poetry-env` — runs `poetry install` in the current interpreter (handy once the conda env is active).

If you'd like I can add a small GitHub Actions job to exercise `make essentia-env` (non-Docker) in CI as a draft optional job.
### Using Poetry with Essentia

Poetry remains the project's default packaging tool. The recommended flow is:

1. Create and activate the conda/mamba env using `environment.analyze-cpu.yml`. 
2. Run `poetry install` inside the activated env so Poetry installs into that interpreter environment.

Note: avoid adding `essentia` as a Poetry extra; installing that way will attempt to fetch Essentia from PyPI or build from source and may require long native builds on some platforms. Prefer creating the conda environment from `environment.analyze-cpu.yml`, activating it, and running `poetry install` inside the conda environment so Poetry uses the conda-provided Essentia binary.

Our `scripts/setup-analyze.sh` will ensure Poetry is installed inside the `songshare-analyze-cpu` env and run `poetry install` within that environment automatically.

### CI (GitHub Actions) snippet (non-Docker)

Use a separate job for Essentia-enabled tests so normal PRs stay fast:

```yaml
essentia-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: conda-incubator/setup-miniconda@v2
      with:
        environment-file: environment.analyze-cpu.yml
        activate-environment: songshare-analyze-cpu
        auto-update-conda: true
    - name: Install project deps
      run: |
        poetry install
    - name: Run essentia tests
      run: |
        pytest -q -m essentia --maxfail=1
```

If you later decide to use Docker for CI, we can add a small prebuilt image and update this workflow. Docker remains optional.

---

## API Design (proposed) 🔌

- Module: `songshare_analysis/essentia/essentia_extractor.py`

Public functions:

```python
def extract_basic(audio_path: Path) -> dict:  # bpm, beats, onsets, loudness
    ...

def extract_tonal(audio_path: Path) -> dict:  # key, chroma, mfcc_summary, tuning
    ...

def extract_sections(audio_path: Path) -> dict:
    ...

def extract_vocals(vocals_path: Path) -> dict:  # run after optional separation
    ...

def write_analysis_sidecar(audio_path: Path, analysis: dict) -> None:
    ...
```

- Behavior:
  - Throw a clear `RuntimeError` / `ImportError` with install instructions when Essentia is not available.
  - Use a stable JSON sidecar format (`<audio>.analysis.json`) and include `provenance` and `confidence` for every major block.

---

## JSON sidecar schema (example excerpt) 📄

```json
{
  "version": "0.1",
  "provenance": {"tool": "essentia", "version": "2.1", "params": {...}},
  "analysis": {
    "rhythm": {"bpm": 120.0, "beats": [0.51, 1.02, ...], "beat_cv": 0.002},
    "tonal": {"key": "C major", "key_strength": 0.78, "chroma_hist": {...}},
    "mfcc": {"mean": [...], "std": [...]},
    "tuning": {"reference_hz": 440.0, "cents_offset": 0.0}
  }
}
```

We include the JSON Schema at `docs/schemas/essentia-analysis.schema.json` and provide a schema-validation test to assert sidecar compliance (see `src/songshare_analysis/essentia/essentia_schema_test.py`).

---

## ID3 / TXXX mapping rules 🧾

- Write only compact scalars or small arrays to ID3/TXXX frames. Large arrays and per-frame matrices go to the JSON sidecar.
- Write rules:
  - `TBPM` ← `analysis.rhythm.bpm` (if confidence >= 0.6)
  - `TKEY` ← `analysis.tonal.key` (if `key_strength` >= 0.6)
  - `TCON` ← top genre label (model-dependent; only when `top_confidence >= 0.6`)
  - `TXXX:beats` / `TXXX:onsets` ← small arrays only; otherwise omit and rely on sidecar
  - Per-field `TXXX:<field>_confidence` frames should accompany model-dependent writes.
- Always include `TXXX:provenance` referencing the extractor + version + params.
- Persist coarse-grained PANNs per-label decile info into the sidecar at `semantic.genre.panns_deciles` so callers can inspect the same `TXXX:panns` style data without writing numeric probabilities into ID3 frames (TXXX tags contain labels/deciles only; values are formatted as `panns: <label>: <decile>` in `TXXX:panns`).

---

## Heuristics & thresholds ⚖️

- Beat CV thresholds (example defaults):
  - `beat_cv < 0.005` -> likely `clicktrack`
  - `beat_cv > 0.02` -> likely `human`
  - Otherwise -> `uncertain`
- Confidence default: **0.6** for most writes; higher (0.7) for tuning and vocal pitch writes.
- Configurable thresholds via CLI/Config object.

---

## CLI integration

- Add flags to `songshare-analyze id3`:
  - `--analyze` (run Essentia extractors and write sidecar)
  - `--apply-tags` (convert analysis to ID3/TXXX according to thresholds)
  - `--separate-vocals` (optional; runs Demucs/Spleeter first)
  - `--preview` / `--apply --yes` (existing safety flags)

Example:

```bash
songshare-analyze id3 --analyze --apply-tags ./music/01-MySong.mp3
```

---

## Separation & vocals flow 🔪

- If `--separate-vocals` is enabled, run Demucs (or Spleeter fallback) and analyze `vocals` stem with Essentia for vocal pitch, presence, and timbre.
- Store `analysis.stems` entries in the sidecar with `provenance` and `path`.
- Tests: include pre-separated small fixtures to avoid running heavy separation in CI.

---

## Testing strategy 🧪

- Add small fixture set in `tests/fixtures/essentia/` covering:
  - Drum loops (straight, swing, funk, reggae)
  - Short chordal clips (major, minor, 7th)
  - Short vocal snippet
- Unit tests:
  - Validate normalization functions, thresholds, sidecar schema
  - Test `analysis_to_tags` mapping rules
- Integration tests:
  - Minimal Essentia-enabled workflow on tiny fixtures inside a Docker image (separate optional job)

---

## CI considerations ⚙️

- Keep Essentia tests in a separate workflow or job. Use a prebuilt Docker image with Essentia or a Conda environment to avoid long install times.
- Provide matrix entries that *do not* force Essentia for normal PR checks. Prefer an optional workflow (`workflow_dispatch`) so maintainers can run Essentia tests on demand rather than blocking every PR.
- Document how to run the Essentia job locally (using `mamba` / `conda`):

### Running Essentia tests locally

1. Create the Essentia environment (mamba recommended):

```bash
# create or update the env
make essentia-env

# or explicitly with mamba
mamba env create -f environment.analyze-cpu.yml || mamba env update -f environment.analyze-cpu.yml -n songshare-analyze-cpu --prune
```

2. Run the Essentia-specific tests:

```bash
# run the single-file test
make essentia-test

# or run all Essentia-related tests directly
conda run -n songshare-analyze-cpu pytest -q -m essentia
```

3. To run the optional GitHub Actions Essentia workflow: open the repository's **Actions** tab and trigger **Essentia tests** via "Run workflow".

### Quick local convenience

If you'd like a single command to install Mambaforge (if missing), create the Essentia conda env, and run the tests, use the Make target:

```bash
# install mambaforge (if needed), create env, and run tests
make essentia-setup-test

# If you already have mamba/conda and want to skip installer
./scripts/run-analyze-tests.sh --no-install
```

Quick convenience for running analysis with your existing `songshare-analyze-cpu` env:

- Makefile target (recommended):

```bash
make essentia-analyze path=/full/path/to/file.mp3
```

- Small helper script (same behavior):

```bash
./scripts/run-with-analyze.sh /full/path/to/file.mp3
```

Both approaches will ensure the project is installable inside the env (editable install) and then run:

```bash
songshare-analyze id3 /full/path/to/file.mp3 --analyze
```

### Editor setup (VS Code) 🛠️

To make your editor pick up `soundfile`, `essentia`, and type stubs automatically in Visual Studio Code:

1. Select the project's Python interpreter (the `songshare-analyze-cpu` conda env):
   - Command Palette → `Python: Select Interpreter` → choose `songshare-analyze-cpu` (or pick the path: `${env:HOME}/mambaforge/envs/songshare-analyze-cpu/bin/python`).
2. If you prefer workspace settings, the repo supplies a `.vscode/settings.json` that defaults the interpreter to the `songshare-analyze-cpu` env and adds `${workspaceFolder}/typings` to `python.analysis.extraPaths`.

After selecting or configuring the interpreter, reload the window (Developer: Reload Window) to refresh the language server and ensure imports resolve.


---

## Performance & caching 🚀

- Cache sidecars keyed by audio checksum to skip repeated extraction.
- Use parallel workers for batch processing with configurable worker pool size.

---

## Security & UX notes ⚠️

- Default to dry-run; require `--apply --yes` for destructive edits.
- Always keep backups before writing tags (temp `.bak` or tag-only sidecar backup).

---

## Short implementation checklist ✅

1. Add `essentia_extractor.py` with stubs and clear ImportError message.
2. Implement `extract_basic` and `write_analysis_sidecar` and tests.  
3. Add `analysis_to_tags` converter & safe write rules.  
4. Add CLI flags and integration tests (mark heavy tests optional).  
5. Add JSON Schema and fixtures.  
6. Add CI job using Docker image for full tests.

---

## Next step

- If this doc looks good I can open a PR implementing step (1) and add unit tests and a README snippet for local Essentia installation. 

---

*Created by GitHub Copilot.*
