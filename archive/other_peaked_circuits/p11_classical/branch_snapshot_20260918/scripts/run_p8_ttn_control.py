#!/usr/bin/env python3
"""Run exact small iSWAP-grid controls for the P8 TTN gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from p12_recovery.peak.ttn import build_weighted_tree, cut_rank_profile, exact_tree_topk, tree_leaves  # noqa: E402
from p12_recovery.peak.qasm import Gate, PeakQASM  # noqa: E402


def control(n: int, depth: int) -> tuple[PeakQASM, np.ndarray]:
    qc = QuantumCircuit(n)
    edges = [(i, i + 1) for i in range(n - 1)]
    for layer in range(depth):
        for q in range(n):
            qc.u(0.17 * (q + 1), -0.11 * layer, 0.07 * (q + layer + 1), q)
        for a, b in edges[layer % 2 :: 2]:
            qc.iswap(a, b)
    state = Statevector.from_instruction(qc).data
    gates = tuple(Gate("u", (q,), (0.17 * (q + 1), -0.11 * layer, 0.07 * (q + layer + 1),)) for layer in range(depth) for q in range(n))
    gates += tuple(Gate("iswap", edge) for layer in range(depth) for edge in edges[layer % 2 :: 2])
    return PeakQASM(n, gates, ("iswap",)), state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--depth", type=int, default=6)
    args = parser.parse_args()
    started = time.monotonic()
    circuit, state = control(args.n, args.depth)
    tree = build_weighted_tree(circuit)
    rows = cut_rank_profile(state, tree)
    top = exact_tree_topk(state)
    result = {
        "schema": "p12-p8-ttn-exact-control-v1",
        "method_family": "TTN",
        "status": "CONTROL_ONLY",
        "answer_blind": True,
        "n_qubits": args.n,
        "depth": args.depth,
        "tree": tree.as_dict(),
        "cut_rank_profile": rows,
        "top_k": top,
        "tree_leaf_order": list(tree_leaves(tree)),
        "statevector_sha256": hashlib.sha256(np.asarray(state).tobytes()).hexdigest(),
        "runtime_s": time.monotonic() - started,
        "production_promotion": "NOT_ALLOWED_FROM_EXACT_CONTROL_ALONE",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("schema", "status", "n_qubits", "depth", "runtime_s")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
