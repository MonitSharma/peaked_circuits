#!/usr/bin/env bash
set -euo pipefail

# Prepare the separate numerical environment used by the public CPU MPO solver.
# This script is intentionally setup-only: it never launches a long simulation.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${MPO_VENV_DIR:-.venv-mpo-mac}"
SOLVER_DIR="${MPO_SOLVER_DIR:-vendor/peaked-mpo-solver}"
SOLVER_URL="https://github.com/alexgalda-m/peaked-mpo-solver.git"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found. Install Python 3.11 or newer, then rerun this script." >&2
  exit 1
fi

if [[ ! -f "$SOLVER_DIR/src/p9solver/cli.py" ]]; then
  mkdir -p "$(dirname "$SOLVER_DIR")"
  echo "Cloning the public CPU MPO solver into $SOLVER_DIR"
  git clone --depth 1 "$SOLVER_URL" "$SOLVER_DIR"
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"
echo "Installing the pinned MPO numerical stack"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt

echo
echo "MPO environment is ready."
echo "Activate it with: source $VENV_DIR/bin/activate"
echo "Solver checkout: $SOLVER_DIR"
echo
echo "Installed versions:"
"$PYTHON" -c 'import numpy, scipy, qiskit, quimb; print("numpy", numpy.__version__); print("scipy", scipy.__version__); print("qiskit", qiskit.__version__); print("quimb", quimb.__version__)'
echo
echo "BLAS/threadpool information:"
"$PYTHON" -c 'from threadpoolctl import threadpool_info; import numpy; print(threadpool_info())'
