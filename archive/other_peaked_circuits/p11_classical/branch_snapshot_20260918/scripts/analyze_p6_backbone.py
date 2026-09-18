#!/usr/bin/env python3
"""Write weighted P6 ordering/backbone diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from p12_recovery.peak.ordering import compare_orderings, edge_weights  # noqa: E402
from p12_recovery.peak.qasm import parse  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    circuit = parse(args.qasm)
    comparison = compare_orderings(circuit)
    result = {"schema": "p12-p6-weighted-backbone-v1", "problem": "P6", "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(), "n_qubits": circuit.n_qubits, "weighted_edge_count": len(edge_weights(circuit)), "top_weighted_edges": [{"qubits": list(edge), "count": count} for edge, count in sorted(edge_weights(circuit).items(), key=lambda item: (-item[1], item[0]))[:32]], **comparison}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"schema": result["schema"], "best_ordering": result["best_ordering"], "metrics": result["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
