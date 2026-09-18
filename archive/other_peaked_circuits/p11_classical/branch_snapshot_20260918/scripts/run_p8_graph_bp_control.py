#!/usr/bin/env python3
"""Run a positive, tree-factorized graph-BP control; target inputs are excluded."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from p12_recovery.peak.graph_bp import BinaryPairwiseGraph  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    n = 10
    unary = np.array([[1.0, 1.0 + 0.03 * (index + 1)] for index in range(n)])
    pairwise = {(index, index + 1): np.array([[4.0, 0.15], [0.15, 4.0]]) for index in range(n - 1)}
    graph = BinaryPairwiseGraph(unary, pairwise)
    bp = graph.sum_product(max_iter=200, tolerance=1e-12)
    top = graph.top_k(k=8)
    result = {
        "schema": "p12-p8-graph-bp-exact-control-v1",
        "status": "CONTROL_ONLY",
        "method_family": "graph-BP",
        "answer_blind": True,
        "n_qubits": n,
        "converged": bp.converged,
        "iterations": bp.iterations,
        "max_message_delta": bp.max_message_delta,
        "top_k": top,
        "production_promotion": "NOT_ALLOWED_FROM_PAIRWISE_CONTROL_ALONE",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("schema", "status", "converged", "iterations")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
