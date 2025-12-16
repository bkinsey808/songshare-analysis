# Simple Makefile for common operations
.PHONY: help venv install test lint format clean

help:
	@echo "Available commands: venv, install, test, lint, format, clean"

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
		poetry run mypy --strict src tests; \
	else \
		. .venv/bin/activate && mypy --strict src tests; \
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
