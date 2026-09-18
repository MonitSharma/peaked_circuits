#!/usr/bin/env bash
set -euo pipefail

# Complete non-hardware setup for a fresh macOS checkout.
# Creates two environments because the recovery application and the research
# MPO solver intentionally use different numerical dependency pins.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MAIN_VENV="${MAIN_VENV_DIR:-.venv}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found. Install Python 3.11 or newer, then rerun this script." >&2
  exit 1
fi

if [[ ! -x "$MAIN_VENV/bin/python" ]]; then
  echo "Creating $MAIN_VENV"
  python3 -m venv "$MAIN_VENV"
fi

PYTHON="$MAIN_VENV/bin/python"
echo "Installing the main recovery application, development tools, and compile-only quantum SDKs"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e '.[dev,quantum]'

bash scripts/setup_mpo_mac.sh

echo
echo "Complete Mac setup is ready."
echo "Main environment: source $MAIN_VENV/bin/activate"
echo "MPO environment:  source .venv-mpo-mac/bin/activate"
echo "Run the P9 benchmark with: bash scripts/benchmark_p9_mac.sh"
