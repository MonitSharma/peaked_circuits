#!/usr/bin/env bash
set -euo pipefail

THREADS="${P11_THREADS:-}"

# Infer --threads from wrapped command if not explicitly provided.
if [[ -z "$THREADS" ]]; then
    prev=""
    for arg in "$@"; do
        if [[ "$prev" == "--threads" ]]; then
            THREADS="$arg"
            break
        fi
        prev="$arg"
    done
fi

THREADS="${THREADS:-18}"
NODE_MODE="${P11_NUMA_MODE:-}"

if [[ -z "$NODE_MODE" ]]; then
    if (( THREADS <= 18 )); then
        NODE_MODE="one_node"
    elif (( THREADS <= 36 )); then
        NODE_MODE="two_nodes"
    else
        NODE_MODE="four_nodes"
    fi
fi

export OMP_NUM_THREADS="$THREADS"
export MKL_NUM_THREADS="$THREADS"
export OPENBLAS_NUM_THREADS="$THREADS"
export NUMBA_NUM_THREADS="$THREADS"
export BLIS_NUM_THREADS="$THREADS"
export NUMEXPR_NUM_THREADS="$THREADS"
export PYTHONUNBUFFERED=1

case "$NODE_MODE" in
    one_node)
        CPUSET="${P11_CPUSET:-0-17}"
        MEMNODES="${P11_MEMNODES:-0}"
        echo "[NUMA] mode=one_node threads=$THREADS physical_cpus=$CPUSET memory=$MEMNODES" >&2
        exec numactl \
            --physcpubind="$CPUSET" \
            --membind="$MEMNODES" \
            "$@"
        ;;

    two_nodes)
        CPUSET="${P11_CPUSET:-0-35}"
        MEMNODES="${P11_MEMNODES:-0,1}"
        echo "[NUMA] mode=two_nodes threads=$THREADS physical_cpus=$CPUSET memory=$MEMNODES" >&2
        exec numactl \
            --physcpubind="$CPUSET" \
            --membind="$MEMNODES" \
            "$@"
        ;;

    four_nodes)
        CPUSET="${P11_CPUSET:-0-71}"
        echo "[NUMA] mode=four_nodes threads=$THREADS physical_cpus=$CPUSET memory=interleave-all" >&2
        exec numactl \
            --physcpubind="$CPUSET" \
            --interleave=all \
            "$@"
        ;;

    *)
        echo "Unknown P11_NUMA_MODE=$NODE_MODE" >&2
        exit 2
        ;;
esac
