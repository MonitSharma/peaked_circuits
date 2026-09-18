#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
THREADS="${PPS_THREADS:-18}"
NODE="${PPS_NUMA_NODE:-0}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1
export JULIA_NUM_THREADS="$THREADS"
JULIA_BIN="${JULIA_BIN:-$HOME/tools/julia-1.10.10/bin/julia}"
if [[ "${PPS_NO_NUMACTL:-0}" == 1 ]]; then
  exec "$JULIA_BIN" --project="$ROOT/julia/pps" "$@"
fi
exec numactl --cpunodebind="$NODE" --membind="$NODE" \
  "$JULIA_BIN" --project="$ROOT/julia/pps" "$@"
