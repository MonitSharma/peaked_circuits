#!/usr/bin/env python3
"""Derive P8 graph-BP factors from a bounded PEPS environment.

This stage is diagnostic only. It refuses to turn non-positive or non-converged
environment estimates into a recovery candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn
from qiskit import QuantumCircuit

from p12_recovery.peak.graph_bp import BinaryPairwiseGraph

ISWAP = np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]], dtype=np.complex128)
P0 = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.complex128)


def run(args: argparse.Namespace) -> dict:
    source = Path(args.qasm)
    qc = QuantumCircuit.from_qasm_file(str(source))
    qc.remove_final_measurements()
    edges = sorted({tuple(sorted(qc.find_bit(q).index for q in instruction.qubits)) for instruction in qc.data if len(instruction.qubits) == 2})
    peps = qtn.CircuitPEPSSimpleUpdate(N=qc.num_qubits, edges=edges, max_bond=args.max_bond, cutoff=args.cutoff, dtype="complex128", renorm=True)
    started = time.monotonic()
    for instruction in qc.data:
        operation = instruction.operation
        qubits = [qc.find_bit(q).index for q in instruction.qubits]
        if operation.name in {"u", "u3"}:
            peps.apply_gate("U3", *map(float, operation.params), qubits[0])
        elif operation.name == "iswap":
            peps.apply_gate(ISWAP, *qubits)
        else:
            raise ValueError(f"unsupported operation: {operation.name}")
    p0 = [float(np.real(peps.local_expectation(P0, [site], max_distance=args.max_distance, normalized=True))) for site in range(qc.num_qubits)]
    unary = np.asarray([[value, 1.0 - value] for value in p0], dtype=float)
    pairwise: dict[tuple[int, int], np.ndarray] = {}
    invalid: list[dict[str, object]] = []
    projected: list[dict[str, object]] = []
    for left, right in edges:
        p00 = float(np.real(peps.local_expectation(np.kron(P0, P0), [left, right], max_distance=args.max_distance, normalized=True)))
        matrix = np.asarray([[p00, p0[left] - p00], [p0[right] - p00, 1.0 - p0[left] - p0[right] + p00]], dtype=float)
        if not np.all(np.isfinite(matrix)) or np.any(matrix <= args.positivity_epsilon):
            raw_matrix = matrix.copy()
            if args.project_invalid and np.all(np.isfinite(matrix)):
                lower = max(args.positivity_epsilon, p0[left] + p0[right] - 1.0 + args.positivity_epsilon)
                upper = min(p0[left], p0[right]) - args.positivity_epsilon
                clipped = min(max(p00, lower), upper)
                matrix = np.asarray([[clipped, p0[left] - clipped], [p0[right] - clipped, 1.0 - p0[left] - p0[right] + clipped]], dtype=float)
                projected.append({"edge": [left, right], "raw_p00": p00, "projected_p00": clipped, "absolute_delta": abs(clipped - p00), "raw_min_factor": float(np.min(raw_matrix))})
                pairwise[(left, right)] = matrix / matrix.sum()
            else:
                invalid.append({"edge": [left, right], "min_factor": float(np.min(matrix)), "matrix": matrix.tolist()})
        else:
            pairwise[(left, right)] = matrix / matrix.sum()
    result: dict[str, object] = {
        "schema": "p12-p8-graph-bp-environment-v1",
        "status": "COMPLETE_DIAGNOSTIC",
        "problem": "P8",
        "method_family": "graph-BP",
        "answer_blind": True,
        "qasm_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "max_bond": args.max_bond,
        "max_distance": args.max_distance,
        "edge_count": len(edges),
        "invalid_factor_count": len(invalid),
        "invalid_factors": invalid[:16],
        "projected_factor_count": len(projected),
        "projected_factors": projected[:16],
        "projection_enabled": args.project_invalid,
        "factor_min": min((float(np.min(matrix)) for matrix in pairwise.values()), default=None),
        "runtime_s": time.monotonic() - started,
        "promotion": "REJECTED_INVALID_ENVIRONMENT_FACTORS" if invalid else "PENDING_CONVERGENCE_GATE",
    }
    if not invalid:
        graph = BinaryPairwiseGraph(unary, pairwise)
        bp = graph.sum_product(max_iter=args.max_iter, tolerance=args.tolerance, damping=args.damping)
        result.update({"converged": bp.converged, "iterations": bp.iterations, "max_message_delta": bp.max_message_delta, "beliefs": bp.beliefs.tolist(), "product_marginal_diagnostic": "".join("1" if row[1] > row[0] else "0" for row in bp.beliefs), "promotion": "PROMISING_CANDIDATE_FAMILY" if bp.converged and not projected else "METHOD_REJECTED_LARGE_ENVIRONMENT_PROJECTION" if bp.converged else "NONCONVERGED"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-bond", type=int, default=4)
    parser.add_argument("--cutoff", type=float, default=1e-10)
    parser.add_argument("--max-distance", type=int, default=2)
    parser.add_argument("--max-iter", type=int, default=200)
    parser.add_argument("--tolerance", type=float, default=1e-10)
    parser.add_argument("--damping", type=float, default=0.2)
    parser.add_argument("--positivity-epsilon", type=float, default=1e-12)
    parser.add_argument("--project-invalid", action="store_true", help="project invalid pair p00 into the valid Frechet interval; never promotes automatically")
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        result = {"schema": "p12-p8-graph-bp-environment-v1", "status": "ABORTED", "answer_blind": True, "reason": f"{type(exc).__name__}: {exc}"}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result.get(key) for key in ("schema", "invalid_factor_count", "converged", "iterations", "promotion", "runtime_s")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
