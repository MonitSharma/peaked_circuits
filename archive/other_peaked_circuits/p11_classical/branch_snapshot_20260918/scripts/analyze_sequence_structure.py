#!/usr/bin/env python3
# ruff: noqa: E402
"""Bounded ordered-interaction matching with fair shuffled-order controls."""

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

from structural.qasm_events import parse_qasm
from structural.sequence_matching import sequence_assignment


def _edges(circuit, start: int, stop: int) -> np.ndarray:
    return np.asarray([event.wires for event in circuit.two_qubit[start:stop]], dtype=int)


def analyze(args: argparse.Namespace) -> dict:
    circuit = parse_qasm(args.qasm)
    center = circuit.n_two_qubit // 2
    largest = max(args.windows)
    midpoints = range(
        max(largest, center - args.radius),
        min(circuit.n_two_qubit - largest, center + args.radius + 1),
        args.step,
    )
    records = []
    for window in args.windows:
        for midpoint in midpoints:
            left = _edges(circuit, midpoint - window, midpoint)
            right = _edges(circuit, midpoint, midpoint + window)[::-1]
            actual = sequence_assignment(
                left,
                right,
                n_qubits=circuit.n_qubits,
                seed=args.seed + midpoint + window,
                restarts=args.restarts,
            )
            shuffled_scores = []
            for trial in range(args.null_trials):
                rng = np.random.default_rng(
                    args.seed + 100000 + trial * 1009 + midpoint + window
                )
                shuffled = right.copy()
                rng.shuffle(shuffled, axis=0)
                shuffled_scores.append(
                    sequence_assignment(
                        left,
                        shuffled,
                        n_qubits=circuit.n_qubits,
                        seed=args.seed + 200000 + trial * 1013 + midpoint + window,
                        restarts=args.restarts,
                    ).score
                )
            mismatch_start = min(circuit.n_two_qubit, midpoint + 2 * window)
            mismatch = _edges(circuit, mismatch_start, min(circuit.n_two_qubit, mismatch_start + window))
            mismatch_score = (
                sequence_assignment(
                    left,
                    mismatch,
                    n_qubits=circuit.n_qubits,
                    seed=args.seed + 300000 + midpoint + window,
                    restarts=args.restarts,
                ).score
                if len(mismatch) == window
                else None
            )
            null = np.asarray(shuffled_scores)
            std = float(np.std(null, ddof=1)) if len(null) > 1 else 0.0
            records.append(
                {
                    "midpoint_index": midpoint,
                    "window": window,
                    "score": actual.score,
                    "null_mean": float(np.mean(null)),
                    "null_std": std,
                    "z": (actual.score - float(np.mean(null))) / std if std else 0.0,
                    "empirical_p": float((1 + np.count_nonzero(null >= actual.score)) / (len(null) + 1)),
                    "mismatched_window_score": mismatch_score,
                    "permutation": list(actual.permutation),
                    "optimizer_passes": actual.passes,
                }
            )
    best_by_window = {
        str(window): max(
            (record for record in records if record["window"] == window),
            key=lambda record: record["score"],
        )
        for window in args.windows
    }
    best_permutations = [np.asarray(record["permutation"]) for record in best_by_window.values()]
    stability = float(
        np.mean(
            [
                np.mean(best_permutations[i] == best_permutations[j])
                for i in range(len(best_permutations))
                for j in range(i + 1, len(best_permutations))
            ]
        )
    ) if len(best_permutations) > 1 else 1.0
    result = {
        "schema": "hqap-sequence-structure-v1",
        "label": args.label,
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": circuit.n_qubits,
        "n_two_qubit": circuit.n_two_qubit,
        "search": vars(args) | {"qasm": str(args.qasm), "output": str(args.output)},
        "best_by_window": best_by_window,
        "neighboring_window_permutation_stability": stability,
        "records": records,
        "null_control_note": "Shuffled-order controls rerun the same bounded optimizer and are therefore fairer than fixed random-permutation baselines.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = ["midpoint_index", "window", "score", "null_mean", "null_std", "z", "empirical_p", "mismatched_window_score"]
    with (args.output / "sequence_scores.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: record[field] for field in fields} for record in records)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    for window in args.windows:
        subset = sorted((r for r in records if r["window"] == window), key=lambda r: r["midpoint_index"])
        axis.plot([r["midpoint_index"] for r in subset], [r["score"] for r in subset], marker="o", label=f"W={window}")
        axis.plot([r["midpoint_index"] for r in subset], [r["null_mean"] for r in subset], linestyle="--", alpha=0.7)
    axis.set(xlabel="Candidate midpoint (2q index)", ylabel="Optimized ordered-edge agreement", title=f"{args.label} sequence-aware mirror test")
    axis.legend()
    figure.tight_layout()
    figure.savefig(args.output / "sequence_match_vs_shuffled.png", dpi=220)
    plt.close(figure)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--radius", type=int, default=128)
    parser.add_argument("--step", type=int, default=32)
    parser.add_argument("--windows", type=int, nargs="+", default=[64, 128, 256])
    parser.add_argument("--null-trials", type=int, default=32)
    parser.add_argument("--restarts", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    print(json.dumps(analyze(args)["best_by_window"], indent=2))


if __name__ == "__main__":
    main()
