#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="0.1.0"
DIST_DIR="${REPO_ROOT}/dist"

echo "==> Building Typist standalone binary for macOS..."
mkdir -p "${DIST_DIR}"

python3 -m pip install --upgrade pip
python3 -m pip install -e "${REPO_ROOT}[cross-platform]"
python3 -m pip install pyinstaller

pyinstaller --clean \
    --name typist \
    --onefile \
    --paths "${REPO_ROOT}/src" \
    --hidden-import typist \
    --hidden-import pynput \
    --hidden-import hid \
    --hidden-import sounddevice \
    --hidden-import httpx \
    --hidden-import dotenv \
    "${REPO_ROOT}/src/typist/main.py"

echo "==> Packaging macOS tarball..."
tar -czf "${DIST_DIR}/typist-macos-${VERSION}.tar.gz" -C "${DIST_DIR}" typist

echo "==> Created: ${DIST_DIR}/typist-macos-${VERSION}.tar.gz"
