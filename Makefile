# Simple Makefile for common operations
.PHONY: help venv install test lint format clean

help:
	@echo "Available commands: venv, install, install-mamba, essentia-env, poetry-env, test, lint, format, clean"

install-mamba:
	@echo "Install Mambaforge locally (user-local installer)"
	@if command -v curl >/dev/null 2>&1; then \
		./scripts/install-mambaforge.sh; \
	else \
		echo "curl is required to download the installer. Please run it manually: https://github.com/conda-forge/miniforge/releases"; \
	fi

# Create the optional Essentia conda/mamba environment and run poetry install inside it
essentia-env:
	@echo "Create Essentia conda environment using environment.essentia.yml"
	@if command -v mamba >/dev/null 2>&1; then \
		mamba env create -f environment.essentia.yml || mamba env update -f environment.essentia.yml -n songshare-essentia --prune; \
	else \
		if command -v conda >/dev/null 2>&1; then \
			conda env create -f environment.essentia.yml || conda env update -f environment.essentia.yml -n songshare-essentia --prune; \
		else \
			echo "conda or mamba is required. Run 'make install-mamba' to install a user-local mamba."; exit 1; \
		fi; \
	fi
	@echo "Activate the env and install project packages with poetry:"
	@echo "  conda activate songshare-essentia && poetry install"

poetry-env:
	@echo "Install project into the current Python environment using Poetry"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
	else \
		echo "Poetry isn't installed. Install it from https://python-poetry.org/docs/"; exit 1; \
	fi

venv:
	python3 -m venv .venv
	@echo "Created virtualenv in .venv. Activate with: source .venv/bin/activate"

install: venv
	@echo "Installing dependencies with Poetry (preferred) or via pip fallback"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
	else \
		. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt && pip install -r requirements-dev.txt; \
	fi

export-reqs:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry export -f requirements.txt --without-hashes -o requirements.txt; \
		poetry export -f requirements.txt --dev --without-hashes -o requirements-dev.txt; \
	else \
		@echo "Install poetry to export requirements: https://python-poetry.org/docs/"; \
	fi

test:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pytest; \
	else \
		. .venv/bin/activate && pytest; \
	fi

lint:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run ruff check . && poetry run isort --check-only . && poetry run black --check .; \
	else \
		. .venv/bin/activate && ruff check . && isort --check-only . && black --check .; \
	fi

typecheck:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pyright src; \
	else \
		. .venv/bin/activate && pyright src; \
	fi

format:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run ruff check --fix . && poetry run isort . && poetry run black . && poetry run ruff check --fix .; \
	else \
		. .venv/bin/activate && ruff check --fix . && isort . && black . && ruff check --fix .; \
	fi

clean:
	rm -rf .venv build dist *.egg-info
	rm -rf .pytest_cache

essentia-test: essentia-env
	@echo "Running essentia tests in conda env 'songshare-essentia'"
	@conda run -n songshare-essentia pytest src/songshare_analysis/test_essentia_mp3.py -q

# Convenience: install mambaforge if needed, create env, and run essentia tests
essentia-setup-test:
	@echo "Run Mambaforge install (if needed), create 'songshare-essentia' env, and run tests"
	@./scripts/run-essentia-tests.sh
