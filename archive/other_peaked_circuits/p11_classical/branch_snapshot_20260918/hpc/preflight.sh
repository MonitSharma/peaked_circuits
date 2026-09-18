#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ ! -x "$ROOT/.venv-hpc/bin/python" ]]; then bash "$ROOT/hpc/bootstrap_env.sh"; fi
"$ROOT/.venv-hpc/bin/python" "$ROOT/scripts/hpc_preflight.py" --repo-root "$ROOT" --output-dir "$ROOT/results/hpc_preflight"
