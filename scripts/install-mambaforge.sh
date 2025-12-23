#!/usr/bin/env bash
set -euo pipefail

# Simple installer for Mambaforge (user-local) for Linux/macOS x86_64 or aarch64
# Usage: ./scripts/install-mambaforge.sh
# This does NOT require sudo and installs to $HOME/mambaforge by default.

PREFIX_DIR="$HOME/mambaforge"

echo "Detecting platform..."
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "${ARCH}" in
  x86_64|amd64) ARCH_ID="x86_64" ;; 
  aarch64|arm64) ARCH_ID="aarch64" ;;
  *) echo "Unsupported arch: ${ARCH}"; exit 1 ;;
esac

if [[ "${OS}" != "linux" && "${OS}" != "darwin" ]]; then
  echo "Unsupported OS: ${OS}. Please install Mambaforge manually from https://github.com/conda-forge/miniforge/releases"
  exit 1
fi

# Build filename (use upstream release naming conventions)
if [[ "${OS}" == "linux" ]]; then
  FNAME="Mambaforge-Linux-${ARCH_ID}.sh"
else
  FNAME="Mambaforge-MacOSX-${ARCH_ID}.sh"
fi

URL="https://github.com/conda-forge/miniforge/releases/latest/download/${FNAME}"

# Try downloading installer; try alternate names if the primary asset isn't present
CANDIDATES=("${FNAME}" "Miniforge3-${OS}-${ARCH_ID}.sh" "Miniforge3-Linux-${ARCH_ID}.sh" "Mambaforge-Linux-${ARCH_ID}.sh")
FOUND=0
for C in "${CANDIDATES[@]}"; do
  URL="https://github.com/conda-forge/miniforge/releases/latest/download/${C}"
  echo "Attempting download: ${URL}"
  if curl -fsSL -o /tmp/${C} "${URL}"; then
    FNAME="${C}"
    FOUND=1
    break
  else
    echo "Download failed for ${C}"
  fi
done

if [[ ${FOUND} -ne 1 ]]; then
  echo "Could not download any installer from GitHub releases; please install Mambaforge/Miniforge manually."
  exit 1
fi

chmod +x /tmp/${FNAME}

echo "Installing to ${PREFIX_DIR} (user-local)..."
# Run installer in batch mode
/tmp/${FNAME} -b -p "${PREFIX_DIR}"

echo "Adding ${PREFIX_DIR}/bin to PATH for this session. To persist, add it to your shell rc (e.g., ~/.bashrc)."
export PATH="${PREFIX_DIR}/bin:${PATH}"

echo "Mambaforge installed to ${PREFIX_DIR}. Run:"
echo "  export PATH=\"${PREFIX_DIR}/bin:\$PATH\""
echo "  source ~/.bashrc or add the export to your shell rc file"

echo "You can now run: mamba env create -f environment.essentia.yml"