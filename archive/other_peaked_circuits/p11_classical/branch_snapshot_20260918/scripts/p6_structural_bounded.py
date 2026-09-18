#!/usr/bin/env python3
"""Plot-free, bounded structural scan for P6."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from structural.qasm_events import parse_qasm
from structural.sequence_matching import sequence_assignment
from structural.unitary_matching import layer_unitary_compatibility, unitary_assignment


def edge_array(circuit, start, stop):
    return np.asarray([event.wires for event in circuit.two_qubit[start:stop]], dtype=int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--null-trials", type=int, default=16)
    ap.add_argument("--seed", type=int, default=20260831)
    args = ap.parse_args()
    circuit = parse_qasm(args.qasm)
    rng = np.random.default_rng(args.seed)

    sequence = []
    center = circuit.n_two_qubit // 2
    for window in (32, 64):
        for midpoint in range(center - 64, center + 65, 32):
            left = edge_array(circuit, midpoint - window, midpoint)
            right = edge_array(circuit, midpoint, midpoint + window)[::-1]
            actual = sequence_assignment(left, right, n_qubits=circuit.n_qubits,
                                         seed=args.seed + midpoint + window, restarts=2)
            null = []
            for trial in range(args.null_trials):
                shuffled = right.copy()
                rng.shuffle(shuffled, axis=0)
                null.append(sequence_assignment(left, shuffled, n_qubits=circuit.n_qubits,
                                                seed=args.seed + trial + midpoint, restarts=2).score)
            null = np.asarray(null)
            mean, std = float(null.mean()), float(null.std(ddof=1))
            sequence.append({"window": window, "midpoint_index": midpoint,
                             "score": actual.score, "null_mean": mean,
                             "null_std": std, "z": (actual.score - mean) / std if std else 0.0,
                             "empirical_p": float((1 + np.count_nonzero(null >= actual.score)) / (len(null) + 1))})

    unitary = []
    midpoint_layer = max(event.layer for event in circuit.events) // 2
    for span in (8, 16):
        for center_layer in range(midpoint_layer - 8, midpoint_layer + 9, 4):
            left = [layer for layer in range(center_layer - span, center_layer)
                    if any(event.layer == layer and event.gate == "u" for event in circuit.events)]
            right = [layer for layer in range(center_layer, center_layer + span)
                     if any(event.layer == layer and event.gate == "u" for event in circuit.events)]
            length = min(len(left), len(right))
            left, right = left[-length:], right[:length]
            if not left:
                continue
            for adjoint in (False, True):
                score, overlap = layer_unitary_compatibility(circuit, left, right, adjoint_right=adjoint)
                permutation, assignment_score, support = unitary_assignment(score, overlap)
                null = [float(np.mean(score[np.arange(circuit.n_qubits), rng.permutation(circuit.n_qubits)]))
                        for _ in range(args.null_trials)]
                null = np.asarray(null)
                mean, std = float(null.mean()), float(null.std(ddof=1))
                unitary.append({"span": span, "center_layer": center_layer,
                                "adjoint_right": adjoint, "score": assignment_score,
                                "null_mean": mean, "null_std": std,
                                "z": (assignment_score - mean) / std if std else 0.0,
                                "support": support, "permutation": permutation.tolist()})

    result = {"schema": "p6-structural-bounded-v1",
              "qasm": str(args.qasm),
              "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
              "n_qubits": circuit.n_qubits, "n_two_qubit": circuit.n_two_qubit,
              "sequence_best": max(sequence, key=lambda row: row["score"]),
              "unitary_best": max(unitary, key=lambda row: row["score"]),
              "sequence_records": sequence, "unitary_records": unitary,
              "interpretation": "bounded lead generation only; no answer bitstring reconstructed"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("sequence_best", "unitary_best")}, indent=2))


if __name__ == "__main__":
    main()
