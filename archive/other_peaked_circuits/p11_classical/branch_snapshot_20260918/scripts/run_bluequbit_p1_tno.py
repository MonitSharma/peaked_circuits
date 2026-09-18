#!/usr/bin/env python3
"""Run the bounded public peaked-circuit TNO idea on blind P1."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import resource
import sys
import time
from pathlib import Path

from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from p12_recovery.bluequbit.tno import contract_core, finish_state, iter_layers, product_marginal_bitstring


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--max-bond", type=int, required=True)
    ap.add_argument("--cutoff", type=float, required=True)
    ap.add_argument("--chunk-size", type=int, default=4)
    ap.add_argument("--max-seconds", type=float, default=120.0)
    args = ap.parse_args()
    if platform.system() != "Darwin":
        raise SystemExit("P1 TNO runner is Mac-only")
    qc = QuantumCircuit.from_qasm_file(str(args.qasm))
    qc.remove_final_measurements()
    layers = list(iter_layers(qc))
    started = time.monotonic()
    result = {"schema": "bluequbit-p1-v2-tno-run-v1", "blind": True, "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(), "configuration": {"max_bond": args.max_bond, "cutoff": args.cutoff, "chunk_size": args.chunk_size, "max_seconds": args.max_seconds, "method": "public_mirrored_tno_cpu", "optimize": "greedy"}, "n_qubits": qc.num_qubits, "layer_count": len(layers)}
    try:
        core, stats, aborted = contract_core(layers, chunk_size=args.chunk_size, max_bond=args.max_bond, cutoff=args.cutoff, max_seconds=args.max_seconds)
        result["core_trace"] = stats
        result["aborted"] = "wall_time_abort" if aborted else None
        if not aborted:
            state = finish_state(core, max_bond=args.max_bond, cutoff=args.cutoff)
            bitstring, p0s = product_marginal_bitstring(state)
            result.update({"top1_product_marginal": bitstring, "p0_marginals": p0s, "final_max_bond": int(state.max_bond() or 1)})
    except Exception as exc:
        result.update({"aborted": "exception", "error_type": type(exc).__name__, "error": str(exc)})
    result.update({"runtime_s": time.monotonic() - started, "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
