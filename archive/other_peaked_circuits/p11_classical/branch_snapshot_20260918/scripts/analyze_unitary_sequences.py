#!/usr/bin/env python3
# ruff: noqa: E402
"""Bounded P9 continuous-unitary sequence matching with shuffled controls."""

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

from structural.patch_unitary import gate_matrix
from structural.qasm_events import parse_qasm
from structural.unitary_sequence import sequence_assignment


def _sequences(circuit, start: int, stop: int, *, reverse: bool = False):
    start_event = next(i for i, event in enumerate(circuit.events) if event.q2_index == start)
    stop_event = next(
        (i for i, event in enumerate(circuit.events) if event.q2_index == stop),
        len(circuit.events),
    )
    result = [[] for _ in range(circuit.n_qubits)]
    for event in circuit.events[start_event:stop_event]:
        if event.gate == "u":
            result[event.wires[0]].append(gate_matrix(event))
    if reverse:
        result = [list(reversed(sequence)) for sequence in result]
    return result


def analyze(args: argparse.Namespace) -> dict:
    circuit = parse_qasm(args.qasm)
    center = circuit.n_two_qubit // 2
    records = []
    for window in args.windows:
        left = _sequences(circuit, center - window, center)
        right = _sequences(circuit, center, center + window, reverse=True)
        actual = sequence_assignment(left, right, adjoint_left=args.adjoint_left)
        null_scores = []
        for trial in range(args.null_trials):
            shuffled = [sequence.copy() for sequence in right]
            rng = np.random.default_rng(args.seed + trial + window)
            for sequence in shuffled:
                rng.shuffle(sequence)
            null_scores.append(
                sequence_assignment(left, shuffled, adjoint_left=args.adjoint_left).score
            )
        null = np.asarray(null_scores)
        mean, std = float(null.mean()), float(null.std(ddof=1))
        mismatch_start = min(circuit.n_two_qubit, center + 2 * window)
        mismatch = _sequences(circuit, mismatch_start, mismatch_start + window)
        mismatch_score = sequence_assignment(
            left, mismatch, adjoint_left=args.adjoint_left
        ).score if len(mismatch[0]) or len(left[0]) else 0.0
        records.append(
            {
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
    permutations = [np.asarray(record["permutation"]) for record in records]
    stability = float(
        np.mean(
            [
                np.mean(permutations[i] == permutations[j])
                for i in range(len(permutations))
                for j in range(i + 1, len(permutations))
            ]
        )
    ) if len(permutations) > 1 else 1.0
    result = {
        "schema": "p9-unitary-sequence-v1",
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "center_q2_index": center,
        "windows": args.windows,
        "adjoint_left": args.adjoint_left,
        "null_trials": args.null_trials,
        "neighboring_window_permutation_stability": stability,
        "records": records,
        "null_control_note": "Each shuffled control reruns the same DTW plus Hungarian assignment after independently shuffling each right-wire unitary sequence.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = ["window", "score", "null_mean", "null_std", "z", "empirical_p", "mismatched_score"]
    with (args.output / "scores.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: record[field] for field in fields} for record in records)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(args.windows, [record["score"] for record in records], marker="o", label="mirror")
    axis.plot(args.windows, [record["null_mean"] for record in records], marker="x", label="shuffled null")
    axis.plot(args.windows, [record["mismatched_score"] for record in records], marker="s", label="mismatched")
    axis.set(xlabel="2q-event window", ylabel="DTW unitary similarity", title="P9 continuous-unitary sequence test")
    axis.legend()
    figure.tight_layout()
    figure.savefig(args.output / "unitary_sequence_vs_controls.png", dpi=220)
    plt.close(figure)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--windows", type=int, nargs="+", default=[64, 128, 256])
    parser.add_argument("--null-trials", type=int, default=16)
    parser.add_argument("--adjoint-left", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    print(json.dumps(analyze(args), indent=2))


if __name__ == "__main__":
    main()
