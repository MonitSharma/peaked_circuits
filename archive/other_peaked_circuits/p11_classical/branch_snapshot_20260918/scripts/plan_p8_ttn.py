#!/usr/bin/env python3
"""Build an answer-blind weighted TTN topology plan for P8."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from p12_recovery.peak.qasm import parse  # noqa: E402
from p12_recovery.peak.ttn import build_weighted_tree, tree_leaves  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    circuit = parse(args.qasm)
    tree = build_weighted_tree(circuit)
    payload = {
        "schema": "p12-p8-ttn-topology-plan-v1",
        "problem": "P8",
        "method_family": "TTN",
        "status": "TOPOLOGY_ONLY",
        "answer_blind": True,
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": circuit.n_qubits,
        "leaf_order": list(tree_leaves(tree)),
        "tree": tree.as_dict(),
        "production_promotion": "BLOCKED_UNTIL_EXACT_CONTROLS_AND_ENVIRONMENT_DECODER_PASS",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({k: payload[k] for k in ("schema", "status", "n_qubits", "qasm_sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
