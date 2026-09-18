#!/usr/bin/env bash
set -euo pipefail

# Run bounded, comparable P9 smoke benchmarks. This is deliberately not a full
# P12 run and does not contact Quantinuum or consume HQCs.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${MPO_VENV_DIR:-.venv-mpo-mac}"
SOLVER_DIR="${MPO_SOLVER_DIR:-vendor/peaked-mpo-solver}"
QASM="$SOLVER_DIR/circ/peaked_circuit_P9_Hqap_56x1917.qasm"
EXPECTED="01101110111001100000100000001010011100101101010111110111"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Missing $VENV_DIR. Run scripts/setup_mpo_mac.sh first." >&2
  exit 1
fi
if [[ ! -f "$SOLVER_DIR/src/p9solver/cli.py" || ! -f "$QASM" ]]; then
  echo "Missing solver checkout or P9 QASM at $SOLVER_DIR" >&2
  exit 1
fi

PYTHON="$VENV_DIR/bin/python"
mkdir -p results/simulation

for THREADS in 4 8; do
  TAG="p9_mac_${THREADS}_smoke"
  echo
  echo "=== $TAG: 300 work gates ==="
  "$PYTHON" scripts/run_peaked_mpo_cpu.py \
    --solver-root "$SOLVER_DIR" \
    --threads "$THREADS" \
    --qasm "$QASM" \
    --outdir results/simulation \
    --tag "$TAG" \
    --max-work-gates 300 \
    --samples 0 \
    --cutoff 0.0006 \
    --no-parallel-rewire \
    --expected-bitstring "$EXPECTED"
done

echo
echo "=== Smoke benchmark summaries ==="
"$PYTHON" - <<'PY'
import json
from pathlib import Path

fields = [
    "compress_time_s",
    "last_work_consumed",
    "termination_reason",
    "peak_max_bond",
    "peak_total_elems",
    "matches_expected_bitstring",
]
for path in sorted(Path("results/simulation").glob("p9_mac_*_smoke/summary.json")):
    data = json.loads(path.read_text())
    print(path.parent.name)
    print({field: data.get(field) for field in fields})
PY
