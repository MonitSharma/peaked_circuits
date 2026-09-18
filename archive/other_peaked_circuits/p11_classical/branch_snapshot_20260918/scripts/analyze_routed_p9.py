#!/usr/bin/env python3
# ruff: noqa: E402
"""Route the supervised P9 halves to a line and test ordered interaction matching."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from structural.sequence_matching import sequence_assignment


def _routed_halves(qasm: Path, *, seed: int):
    from qiskit import QuantumCircuit, transpile
    from qiskit.transpiler import CouplingMap

    circuit = QuantumCircuit.from_qasm_file(qasm)
    midpoint = len(circuit.data) // 2

    def make_part(instructions, inverse: bool) -> QuantumCircuit:
        part = QuantumCircuit(circuit.num_qubits)
        for instruction in instructions:
            part.append(instruction.operation, instruction.qubits, instruction.clbits)
        return part.inverse() if inverse else part

    coupling = CouplingMap.from_line(circuit.num_qubits)
    routed = []
    for instructions, inverse in (
        (circuit.data[:midpoint], True),
        (circuit.data[midpoint:], False),
    ):
        part = make_part(instructions, inverse)
        routed_circuit = transpile(
            part,
            coupling_map=coupling,
            initial_layout=list(range(circuit.num_qubits)),
            routing_method="sabre",
            optimization_level=0,
            seed_transpiler=seed,
            basis_gates=["u", "cx"],
        )
        edges = np.asarray(
            [
                [routed_circuit.find_bit(qubit).index for qubit in instruction.qubits]
                for instruction in routed_circuit.data
                if instruction.operation.num_qubits == 2
            ],
            dtype=int,
        )
        routed.append((routed_circuit, edges))
    return circuit, routed


def analyze(args: argparse.Namespace) -> dict:
    circuit, routed = _routed_halves(args.qasm, seed=args.seed)
    rows = []
    for start in args.starts:
        for window in args.windows:
            left = routed[0][1][start : start + window]
            right = routed[1][1][start : start + window]
            if len(left) != window or len(right) != window:
                continue
            actual = sequence_assignment(
                left, right, n_qubits=circuit.num_qubits, seed=args.seed + start + window, restarts=args.restarts
            )
            null_scores = []
            for trial in range(args.null_trials):
                shuffled = right.copy()
                np.random.default_rng(args.seed + 10000 + trial + start).shuffle(shuffled, axis=0)
                null_scores.append(
                    sequence_assignment(
                        left,
                        shuffled,
                        n_qubits=circuit.num_qubits,
                        seed=args.seed + 20000 + trial + start,
                        restarts=args.restarts,
                    ).score
                )
            null = np.asarray(null_scores)
            mean, std = float(null.mean()), float(null.std(ddof=1))
            mismatch_start = start + 2 * window
            mismatch = routed[1][1][mismatch_start : mismatch_start + window]
            mismatch_score = (
                sequence_assignment(
                    left, mismatch, n_qubits=circuit.num_qubits, seed=args.seed + 30000 + start, restarts=args.restarts
                ).score
                if len(mismatch) == window
                else None
            )
            rows.append(
                {
                    "start": start,
                    "window": window,
                    "score": actual.score,
                    "null_mean": mean,
                    "null_std": std,
                    "z": (actual.score - mean) / std if std else 0.0,
                    "empirical_p": float((1 + np.count_nonzero(null >= actual.score)) / (len(null) + 1)),
                    "mismatched_score": mismatch_score,
                    "permutation": list(actual.permutation),
                }
            )
    best_by_window = {
        str(window): max((row for row in rows if row["window"] == window), key=lambda row: row["score"])
        for window in args.windows
    }
    permutations = [np.asarray(row["permutation"]) for row in best_by_window.values()]
    stability = float(
        np.mean([np.mean(permutations[i] == permutations[j]) for i in range(len(permutations)) for j in range(i + 1, len(permutations))])
    ) if len(permutations) > 1 else 1.0
    result = {
        "schema": "p9-routed-structure-v1",
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": circuit.num_qubits,
        "original_gate_count": len(circuit.data),
        "routed_gate_counts": [len(item[0].data) for item in routed],
        "routed_two_qubit_counts": [len(item[1]) for item in routed],
        "search": vars(args) | {"qasm": str(args.qasm), "output": str(args.output)},
        "best_by_window": best_by_window,
        "neighboring_window_permutation_stability": stability,
        "records": rows,
        "null_control_note": "The shuffled-order controls rerun the same bounded sequence optimizer on routed halves.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = ["start", "window", "score", "null_mean", "null_std", "z", "empirical_p", "mismatched_score"]
    with (args.output / "scores.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in fields} for row in rows)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    for window in args.windows:
        subset = sorted((row for row in rows if row["window"] == window), key=lambda row: row["start"])
        axis.plot([row["start"] for row in subset], [row["score"] for row in subset], marker="o", label=f"W={window}")
        axis.plot([row["start"] for row in subset], [row["null_mean"] for row in subset], linestyle="--", alpha=0.7)
    axis.set(xlabel="Routed prefix start (2q index)", ylabel="Optimized ordered-edge agreement", title="P9 routed-half structure test")
    axis.legend()
    figure.tight_layout()
    figure.savefig(args.output / "routed_match_vs_shuffled.png", dpi=220)
    plt.close(figure)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--starts", type=int, nargs="+", default=[0, 64, 128, 256])
    parser.add_argument("--windows", type=int, nargs="+", default=[64, 128, 256])
    parser.add_argument("--null-trials", type=int, default=16)
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    print(json.dumps(analyze(args)["best_by_window"], indent=2))


if __name__ == "__main__":
    main()
