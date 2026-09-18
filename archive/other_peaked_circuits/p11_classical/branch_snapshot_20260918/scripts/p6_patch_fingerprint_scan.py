#!/usr/bin/env python3
"""Bounded exact small-patch fingerprint matching around the P6 midpoint."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from compiler.local_synthesis import extract_dependency_blocks
from structural.patch_unitary import patch_unitary, phase_insensitive_fidelity
from structural.qasm_events import parse_qasm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--radius", type=int, default=160)
    ap.add_argument("--max-pairs", type=int, default=2500)
    args = ap.parse_args()
    circuit = parse_qasm(args.qasm)
    midpoint = circuit.n_two_qubit // 2
    blocks = extract_dependency_blocks(circuit, 3, max_global_span=40, max_entanglers=4)
    left = [b for b in blocks if midpoint - args.radius <= b.start < midpoint]
    right = [b for b in blocks if midpoint <= b.start < midpoint + args.radius]
    left = left[-min(len(left), 80):]
    right = right[:min(len(right), 80)]
    prepared = {}
    for block in left + right:
        key = (block.start, block.stop, block.wires)
        prepared[key] = patch_unitary(block.events, block.wires)

    records = []
    for i, lb in enumerate(left):
        for j, rb in enumerate(right):
            if len(records) >= args.max_pairs:
                break
            if len(lb.wires) != len(rb.wires) or lb.old_two_qubit != rb.old_two_qubit:
                continue
            left_u = prepared[(lb.start, lb.stop, lb.wires)]
            best = (-1.0, None, None)
            for perm in itertools.permutations(rb.wires):
                right_u = patch_unitary(rb.events, perm)
                for adjoint in (False, True):
                    candidate = right_u.conj().T if adjoint else right_u
                    score = phase_insensitive_fidelity(left_u, candidate)
                    if score > best[0]:
                        best = (score, list(perm), adjoint)
            records.append({"left_start": lb.start, "right_start": rb.start,
                            "left_wires": list(lb.wires), "right_wires": list(rb.wires),
                            "qubits": len(lb.wires), "left_two_qubit": lb.old_two_qubit,
                            "score": best[0], "right_wire_order": best[1],
                            "adjoint_right": best[2]})
        if len(records) >= args.max_pairs:
            break
    records.sort(key=lambda row: row["score"], reverse=True)
    top = records[:20]
    result = {"schema": "p6-small-patch-fingerprint-v1", "qasm": str(args.qasm),
              "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
              "midpoint_q2": midpoint, "left_blocks": len(left), "right_blocks": len(right),
              "pairs_tested": len(records), "top_matches": top,
              "interpretation": "exact local-unitary patch matches; candidate generation not validated"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"left_blocks": len(left), "right_blocks": len(right),
                      "pairs_tested": len(records), "top_matches": top[:5]}, indent=2))


if __name__ == "__main__":
    main()
