# Simple Makefile for common operations
.PHONY: help install install-mamba essentia-env analyze-env poetry-env test lint format clean

help:
	@echo "Available commands: install, install-mamba, essentia-env (alias: analyze-env), poetry-env, test, lint, format, clean"

# Backwards-compatible alias targets so users can use either name
analyze-env: essentia-env
	@echo "Alias: analyze-env -> essentia-env"

analyze-test: essentia-test
	@echo "Alias: analyze-test -> essentia-test"

analyze-analyze: essentia-analyze
	@echo "Alias: analyze-analyze -> essentia-analyze"

analyze-setup-test: essentia-setup-test
	@echo "Alias: analyze-setup-test -> essentia-setup-test"

install-mamba:
	@echo "Install Mambaforge locally (user-local installer)"
	@if command -v curl >/dev/null 2>&1; then \
		./scripts/install-mambaforge.sh; \
	else \
		echo "curl is required to download the installer. Please run it manually: https://github.com/conda-forge/miniforge/releases"; \
	fi

# Create the optional Essentia conda/mamba environment and run poetry install inside it
essentia-env:
	@echo "Create analyze CPU conda environment using environment.analyze-cpu.yml"
	@if command -v mamba >/dev/null 2>&1; then \
		mamba env create -f environment.analyze-cpu.yml || mamba env update -f environment.analyze-cpu.yml -n songshare-analyze-cpu --prune; \
		echo "Environment updated: songshare-analyze-cpu"; \
	else \
		if command -v conda >/dev/null 2>&1; then \
			conda env create -f environment.analyze-cpu.yml || conda env update -f environment.analyze-cpu.yml -n songshare-analyze-cpu --prune; \
			echo "Environment updated: songshare-analyze-cpu"; \
		else \
			echo "conda or mamba is required. Run 'make install-mamba' to install a user-local mamba."; exit 1; \
		fi; \
	fi
	@echo "Activate the env and install project packages with poetry:"
	@echo "  conda activate songshare-analyze-cpu && poetry install"

poetry-env:
	@echo "Install project into the current Python environment using Poetry"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
	else \
		echo "Poetry is not installed. Install it from https://python-poetry.org/docs/"; exit 1; \
	fi

install:
	@echo "Installing dependencies with Poetry (preferred)."
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
		poetry export -f requirements.txt --dev --without-hashes -o requirements-dev.txt; \
	else \
		# If no global Poetry, attempt to provision the Conda env
		if command -v mamba >/dev/null 2>&1 || command -v conda >/dev/null 2>&1; then \
			./scripts/setup-analyze.sh; \
		else \
			echo "Poetry not found and no conda/mamba available. Install Poetry or use a Conda env to run 'poetry install'"; exit 1; \
		fi; \
	fi

test:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pytest; \
	else \
		# If using Conda env, run tests inside it ensuring Poetry is present
		if command -v mamba >/dev/null 2>&1 || command -v conda >/dev/null 2>&1; then \
			./scripts/setup-analyze.sh && mamba run -n songshare-analyze-cpu pytest; \
		else \
			echo "Run tests inside your Conda/Mamba env (e.g., make essentia-env && mamba activate songshare-analyze-cpu && pip install -e . && pytest)"; \
		fi; \
	fi

lint:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run ruff check . && poetry run isort --check-only . && poetry run black --check .; \
	else \
		# Try to set up the analyze env and run lint inside it
		if command -v mamba >/dev/null 2>&1 || command -v conda >/dev/null 2>&1; then \
			./scripts/setup-analyze.sh && mamba run -n songshare-analyze-cpu make lint; \
		else \
			echo "Poetry not found. To run linting use the 'songshare-analyze-cpu' conda env: make essentia-env && mamba run -n songshare-analyze-cpu pip install poetry && mamba run -n songshare-analyze-cpu poetry install && make lint"; \
		fi; \
	fi

typecheck:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run pyright src; \
	else \
		echo "Poetry not found. To run typecheck use the 'songshare-analyze-cpu' conda env: make essentia-env && conda activate songshare-analyze-cpu && pip install -e . && make typecheck"; \
	fi

format:
	@if command -v poetry >/dev/null 2>&1; then \
		poetry run ruff check --fix . && poetry run isort . && poetry run black . && poetry run ruff check --fix .; \
	else \
		echo "Poetry not found. To format code use the 'songshare-analyze-cpu' conda env: make essentia-env && conda activate songshare-analyze-cpu && pip install -e . && make format"; \
	fi

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache

essentia-test: essentia-env
	@echo "Running essentia tests in conda env 'songshare-analyze-cpu'"
	@conda run -n songshare-analyze-cpu pytest src/songshare_analysis/test_essentia_mp3.py -q

# Run the `songshare-analyze` CLI inside the `songshare-analyze-cpu` env so
# users don't have to manually activate the env. Usage:
#   make essentia-analyze path=/full/path/to/file.mp3
essentia-analyze:
	@set -e; \
	if command -v mamba >/dev/null 2>&1; then \
		MCONDA=mamba; \
	elif command -v conda >/dev/null 2>&1; then \
		MCONDA=conda; \
	else \
		echo "mamba or conda required to run this target"; exit 1; \
	fi; \
	if [ -z "$(path)" ]; then \
		echo "Usage: make essentia-analyze path=/full/path/to/file.mp3"; exit 2; \
	fi; \
	# Ensure the project is installable in the env (editable install); ignore
	# failures from pip install (it may already be installed).
	${MCONDA} run -n songshare-analyze-cpu bash -lc 'cd "$(PWD)" && pip install -e . >/dev/null 2>&1 || true'; \
	${MCONDA} run -n songshare-analyze-cpu bash -lc 'songshare-analyze id3 "$(path)" --analyze'

# Convenience: install mambaforge if needed, create env, and run essentia tests
essentia-setup-test:
	@echo "Run Mambaforge install, create 'songshare-analyze-cpu' env, and run tests"
	@./scripts/run-analyze-tests.sh
