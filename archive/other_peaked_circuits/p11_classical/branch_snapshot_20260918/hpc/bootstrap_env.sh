#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VENV="$ROOT/.venv-hpc"
PYTHON_BIN="${P11_HPC_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      version=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
      if [[ "$version" == "3.10" ]]; then PYTHON_BIN=$(command -v "$candidate"); break; fi
    fi
  done
fi
[[ -n "$PYTHON_BIN" ]] || { echo 'Python 3.10 is required by the pinned p9solver stack.' >&2; exit 2; }

"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install -r "$ROOT/requirements-hpc.txt"
"$VENV/bin/python" -m pip install --no-deps --editable "$ROOT"
bash "$ROOT/hpc/bootstrap_solver.sh"

# Install the pinned/patched external MPO solver into the HPC environment.
SOLVER_ROOT="${P11_SOLVER_ROOT:-$ROOT/external/peaked-mpo-solver}"
"$VENV/bin/python" -m pip install --no-deps --editable "$SOLVER_ROOT"

bash "$ROOT/hpc/bootstrap_circuits.sh"
"$VENV/bin/python" - <<'PY'
import importlib
for name in ("numpy", "scipy", "quimb", "cotengra", "numba", "psutil", "threadpoolctl", "p9solver"):
    importlib.import_module(name)
print("HPC import smoke passed")
PY
printf 'HPC environment ready: %s\n' "$VENV"
