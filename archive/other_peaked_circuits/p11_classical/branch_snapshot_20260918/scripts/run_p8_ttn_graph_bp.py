#!/usr/bin/env python3
"""Decode positive TTN marginals with graph belief propagation (diagnostic)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from p12_recovery.peak.graph_bp import BinaryPairwiseGraph  # noqa: E402
from p12_recovery.peak.qasm import parse  # noqa: E402
from p12_recovery.peak.ttn_state import simulate_ttn  # noqa: E402
from run_p8_ttn import gate_matrix  # noqa: E402


def run(args: argparse.Namespace) -> dict[str, object]:
    source = Path(args.qasm)
    circuit = parse(source)
    state = simulate_ttn(circuit, max_bond=args.max_bond, cutoff=args.cutoff, tree_mode=args.tree_mode)
    for gate in circuit.gates:
        if len(gate.qubits) == 1:
            state.apply_one_qubit(gate.qubits[0], gate_matrix(gate))
        else:
            state.apply_two_qubit(gate.qubits[0], gate.qubits[1], gate_matrix(gate))
    edges = sorted({tuple(sorted(gate.qubits)) for gate in circuit.gates if len(gate.qubits) == 2})
    unary, pairwise, total = state.marginal_factors(edges)
    floor = args.positivity_floor
    raw_min = min(float(np.min(unary)), *(float(np.min(matrix)) for matrix in pairwise.values()))
    if raw_min <= floor:
        raise ValueError(f"TTN marginal factor is not strictly above positivity floor: {raw_min}")
    graph = BinaryPairwiseGraph(unary, pairwise)
    bp = graph.sum_product(max_iter=args.max_iter, tolerance=args.tolerance, damping=args.damping)
    belief_bits = "".join("1" if row[1] > row[0] else "0" for row in bp.beliefs)
    return {
        "schema": "p12-p8-ttn-derived-graph-bp-v1",
        "problem": "P8",
        "method_family": "TTN-derived-graph-BP",
        "answer_blind": True,
        "qasm_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "n_qubits": circuit.n_qubits,
        "max_bond": args.max_bond,
        "cutoff": args.cutoff,
        "tree_mode": args.tree_mode,
        "edge_count": len(edges),
        "approximate_total_mass": total,
        "factor_min": raw_min,
        "converged": bp.converged,
        "iterations": bp.iterations,
        "max_message_delta": bp.max_message_delta,
        "diagnostic_bitstring": belief_bits,
        "joint_map_claim": False,
        "promotion": "METHOD_REJECTED_CORRELATED_DIAGNOSTIC" if bp.converged else "NONCONVERGED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-bond", type=int, default=4)
    parser.add_argument("--cutoff", type=float, default=0.01)
    parser.add_argument("--tree-mode", choices=("weighted", "unweighted"), default="weighted")
    parser.add_argument("--max-iter", type=int, default=200)
    parser.add_argument("--tolerance", type=float, default=1e-10)
    parser.add_argument("--damping", type=float, default=0.2)
    parser.add_argument("--positivity-floor", type=float, default=0.0)
    args = parser.parse_args()
    try:
        result = run(args)
        code = 0
    except Exception as exc:
        result = {"schema": "p12-p8-ttn-derived-graph-bp-v1", "problem": "P8", "method_family": "TTN-derived-graph-BP", "status": "ABORTED", "answer_blind": True, "error_type": type(exc).__name__, "error": str(exc)}
        code = 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result.get(key) for key in ("promotion", "converged", "iterations", "factor_min", "diagnostic_bitstring", "error_type", "error")}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
