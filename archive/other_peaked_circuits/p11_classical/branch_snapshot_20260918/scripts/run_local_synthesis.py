#!/usr/bin/env python3
"""Run bounded exact local synthesis and emit JSON/CSV-friendly summaries."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compiler.local_synthesis import extract_blocks, middle_out_order, synthesize_block
from structural.qasm_events import parse_qasm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--block-size", type=int, default=2)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--middle-out", action="store_true")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    circuit = parse_qasm(args.qasm)
    blocks = extract_blocks(circuit, args.block_size, offset=args.offset)
    if args.middle_out:
        blocks = middle_out_order(blocks, len(circuit.events))
    results = [synthesize_block(block) for block in blocks]
    payload = {
        "qasm": str(Path(args.qasm)),
        "block_size": args.block_size,
        "offset": args.offset,
        "middle_out": args.middle_out,
        "blocks": len(blocks),
        "accepted": sum(result.accepted for result in results),
        "old_two_qubit": sum(result.old_two_qubit for result in results),
        "new_two_qubit": sum((result.new_two_qubit or 0) for result in results if result.accepted),
        "permutation_candidates": sum(len(result.tried_permutations) for result in results),
        "results": [
            {
                "start": result.block.start,
                "stop": result.block.stop,
                "wires": result.block.wires,
                "status": result.status,
                "accepted": result.accepted,
                "old_two_qubit": result.old_two_qubit,
                "new_two_qubit": result.new_two_qubit,
                "fidelity": result.fidelity,
                "permutation": result.permutation,
                "tried_permutations": result.tried_permutations,
                "reason": result.reason,
            }
            for result in results
        ],
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with (out / "ledger.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["start", "stop", "wires", "status", "accepted", "old_two_qubit", "new_two_qubit", "fidelity", "permutation", "reason"])
        writer.writeheader()
        for result in results:
            writer.writerow({"start": result.block.start, "stop": result.block.stop, "wires": result.block.wires, "status": result.status, "accepted": result.accepted, "old_two_qubit": result.old_two_qubit, "new_two_qubit": result.new_two_qubit, "fidelity": result.fidelity, "permutation": result.permutation, "reason": result.reason})
    print(json.dumps({key: payload[key] for key in ("blocks", "accepted", "old_two_qubit", "new_two_qubit", "permutation_candidates")}, sort_keys=True))


if __name__ == "__main__":
    main()
