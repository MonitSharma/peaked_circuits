#!/usr/bin/env python3
"""Test whether the P6 layer-207 permutation persists outside its seed patch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from structural.fingerprints import compatibility, layer_fingerprints
from structural.qasm_events import parse_qasm
from structural.sequence_matching import edge_agreement, sequence_assignment


def edges(circuit, start, stop):
    return np.asarray([event.wires for event in circuit.two_qubit[start:stop]], dtype=int)


def constrained_refinement(left, right, mapping, n_qubits, max_swaps=10):
    current = np.asarray(mapping, dtype=int).copy()
    score = edge_agreement(left, right, current)
    accepted = 0
    while accepted < max_swaps:
        best = (score, None)
        for a in range(n_qubits):
            for b in range(a + 1, n_qubits):
                proposal = current.copy()
                proposal[a], proposal[b] = proposal[b], proposal[a]
                candidate = edge_agreement(left, right, proposal)
                if candidate > best[0] + 1e-12:
                    best = (candidate, (a, b))
        if best[1] is None:
            break
        score, (a, b) = best
        current[a], current[b] = current[b], current[a]
        accepted += 1
    return current.tolist(), score, accepted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("scan", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    circuit = parse_qasm(args.qasm)
    scan = json.loads(args.scan.read_text())
    mapping = scan["unitary_best"]["permutation"]
    center_q2 = 1747
    center_layer = scan["unitary_best"]["center_layer"]

    records = []
    for width in (16, 32, 64, 128, 256):
        left = edges(circuit, center_q2 - width, center_q2)
        right = edges(circuit, center_q2, center_q2 + width)[::-1]
        constrained = edge_agreement(left, right, np.asarray(mapping))
        refined_map, refined, swaps = constrained_refinement(
            left, right, mapping, circuit.n_qubits, max_swaps=10
        )
        unconstrained = sequence_assignment(left, right, n_qubits=circuit.n_qubits,
                                            seed=20260831 + width, restarts=4)
        records.append({"q2_width": width, "constrained_edge_score": constrained,
                        "refined_edge_score": refined, "accepted_refinement_swaps": swaps,
                        "unconstrained_edge_score": unconstrained.score,
                        "refined_mapping": refined_map})

    fingerprint_records = []
    for span in (16, 32, 64, 96):
        left = layer_fingerprints(circuit, center_layer - span, center_layer, reverse=True)
        right = layer_fingerprints(circuit, center_layer, center_layer + span)
        matrix = compatibility(left, right)
        mapped = float(np.mean(matrix[np.arange(circuit.n_qubits), mapping]))
        best = np.asarray([matrix[i].max() for i in range(circuit.n_qubits)])
        fingerprint_records.append({"layer_span": span, "fixed_mapping_score": mapped,
                                    "rowwise_best_mean": float(best.mean()),
                                    "mapping_gap": float(best.mean() - mapped)})

    result = {"schema": "p6-constrained-reconstruction-v1",
              "qasm": str(args.qasm),
              "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
              "prior": {"center_q2": center_q2, "center_layer": center_layer,
                        "source_scan": str(args.scan), "permutation": mapping},
              "edge_records": records, "fingerprint_records": fingerprint_records,
              "interpretation": "prior persistence test; no answer bitstring reconstructed",
              "next_action": "retain only if fixed mapping remains competitive at larger widths"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"edge_records": records, "fingerprint_records": fingerprint_records}, indent=2))


if __name__ == "__main__":
    main()
