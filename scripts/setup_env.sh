#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo "Activated virtual environment .venv and installed requirements."