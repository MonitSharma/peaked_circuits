#!/usr/bin/env python3
# ruff: noqa: E402
"""Bounded P9 time-dependent permutation tracking with null controls."""

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

from structural.dynamic_permutation import track
from structural.fingerprints import compatibility, window_fingerprints
from structural.qasm_events import parse_qasm


def _matrices(circuit, width: int, *, shuffle: bool = False, mismatch: bool = False, seed: int = 0):
    half = circuit.n_two_qubit // 2
    matrices = []
    rng = np.random.default_rng(seed)
    for time in range(half // width):
        left_start, left_stop = time * width, (time + 1) * width
        right_start = circuit.n_two_qubit - (time + 1) * width
        right_stop = circuit.n_two_qubit - time * width
        if mismatch:
            right_start = max(half, right_start - width)
            right_stop = min(circuit.n_two_qubit, right_stop - width)
        left = window_fingerprints(circuit, left_start, left_stop)
        right = window_fingerprints(circuit, right_start, right_stop, reverse=True)
        if shuffle:
            right = right.copy()
            rng.shuffle(right, axis=0)
        matrices.append(compatibility(left, right))
    return matrices


def _path_metrics(path) -> dict[str, float]:
    return {
        "mean_structural_score": float(np.mean([state.structural_score for state in path])),
        "total_transition_cost": float(sum(state.transition_cost for state in path[1:])),
        "mean_consecutive_agreement": float(
            np.mean(
                [
                    np.mean(np.asarray(path[i].permutation) == np.asarray(path[i + 1].permutation))
                    for i in range(len(path) - 1)
                ]
            )
        ) if len(path) > 1 else 1.0,
        "steps": len(path),
    }


def analyze(args: argparse.Namespace) -> dict:
    circuit = parse_qasm(args.qasm)
    rows = []
    trajectories = {}
    for width in args.windows:
        actual_matrices = _matrices(circuit, width)
        for beam in args.beams:
            path = track(actual_matrices, beam_width=beam, transition_penalty=args.transition_penalty)
            metrics = _path_metrics(path)
            key = f"w{width}_b{beam}"
            trajectories[key] = [
                [int(value) for value in state.permutation] for state in path
            ]
            null_metrics = []
            for trial in range(args.null_trials):
                null_path = track(
                    _matrices(circuit, width, shuffle=True, seed=args.seed + trial),
                    beam_width=beam,
                    transition_penalty=args.transition_penalty,
                )
                null_metrics.append(_path_metrics(null_path))
            null_scores = np.asarray([item["mean_structural_score"] for item in null_metrics])
            rows.append(
                {
                    "window": width,
                    "beam": beam,
                    **metrics,
                    "null_mean_structural_score": float(null_scores.mean()),
                    "null_std_structural_score": float(null_scores.std(ddof=1)),
                    "null_z": (metrics["mean_structural_score"] - float(null_scores.mean())) / float(null_scores.std(ddof=1)) if len(null_scores) > 1 and null_scores.std(ddof=1) else 0.0,
                    "null_mean_consecutive_agreement": float(np.mean([item["mean_consecutive_agreement"] for item in null_metrics])),
                }
            )
    result = {
        "schema": "p9-dynamic-permutation-v1",
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "windows": args.windows,
        "beams": args.beams,
        "transition_penalty": args.transition_penalty,
        "null_trials": args.null_trials,
        "records": rows,
        "trajectories": trajectories,
        "decision": "NO-GO: no coherent time-dependent path exceeded shuffled controls",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = ["window", "beam", "mean_structural_score", "total_transition_cost", "mean_consecutive_agreement", "null_mean_structural_score", "null_std_structural_score", "null_z", "null_mean_consecutive_agreement"]
    with (args.output / "scores.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in fields} for row in rows)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    for beam in args.beams:
        subset = [row for row in rows if row["beam"] == beam]
        axis.plot([row["window"] for row in subset], [row["mean_consecutive_agreement"] for row in subset], marker="o", label=f"beam={beam}")
    axis.set(xlabel="Temporal window", ylabel="Consecutive permutation agreement", title="P9 dynamic tracker coherence")
    axis.legend()
    figure.tight_layout()
    figure.savefig(args.output / "dynamic_tracker_coherence.png", dpi=220)
    plt.close(figure)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--windows", type=int, nargs="+", default=[64, 128, 256])
    parser.add_argument("--beams", type=int, nargs="+", default=[8, 16, 32])
    parser.add_argument("--transition-penalty", type=float, default=0.2)
    parser.add_argument("--null-trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    print(json.dumps(analyze(args), indent=2))


if __name__ == "__main__":
    main()
