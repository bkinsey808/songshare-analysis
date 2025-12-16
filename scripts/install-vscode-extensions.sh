#!/usr/bin/env bash
set -euo pipefail

EXTENSIONS=(
  ms-python.python
  ms-python.vscode-pylance
  charliermarsh.ruff
  ms-python.black-formatter
  ms-python.isort
  ms-python.mypy-type-checker
  njpwerner.autodocstring
  GitHub.vscode-pull-request-github
)

if ! command -v code >/dev/null 2>&1; then
  echo "VS Code CLI 'code' not found. Install Visual Studio Code and ensure 'code' is on PATH."
  exit 1
fi

for ext in "${EXTENSIONS[@]}"; do
  echo "Installing $ext..."
  code --install-extension "$ext" || echo "Failed to install $ext (maybe already installed)"
done

echo "All done. Open VS Code and reload the window if necessary to activate the extensions." 
