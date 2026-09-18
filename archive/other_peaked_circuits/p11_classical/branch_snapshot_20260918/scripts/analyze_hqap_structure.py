#!/usr/bin/env python3
"""Bounded midpoint/mirror structural analysis for P9 or blind P11."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from structural.fingerprints import compatibility, layer_fingerprints, window_fingerprints
from structural.matching import assignment_significance, hungarian, null_scores
from structural.qasm_events import parse_qasm
from structural.temporal_graph import (
    graph_agreement,
    interaction_matrix,
    layer_interaction_matrix,
    refine_by_transpositions,
    spectral_assignment,
)


def analyze(args: argparse.Namespace) -> dict:
    circuit = parse_qasm(args.qasm)
    axis_count = circuit.n_two_qubit if args.axis == "q2" else max(event.layer for event in circuit.events) + 1
    fingerprint_fn = window_fingerprints if args.axis == "q2" else layer_fingerprints
    graph_fn = interaction_matrix if args.axis == "q2" else layer_interaction_matrix
    center = axis_count // 2
    largest_window = max(args.windows)
    midpoints = range(
        max(largest_window, center - args.radius),
        min(axis_count - largest_window, center + args.radius + 1),
        args.step,
    )
    records: list[dict] = []
    for window in args.windows:
        for midpoint in midpoints:
            left = fingerprint_fn(circuit, midpoint - window, midpoint)
            right = fingerprint_fn(circuit, midpoint, midpoint + window, reverse=True)
            matrix = compatibility(left, right)
            assignment = hungarian(matrix)
            null = null_scores(matrix, trials=args.null_trials, seed=args.seed + midpoint + window)
            significance = assignment_significance(assignment.score, null)
            left_graph = graph_fn(circuit, midpoint - window, midpoint)
            right_graph = graph_fn(circuit, midpoint, midpoint + window)
            spectral = spectral_assignment(left_graph, right_graph)
            refined, refinement_history = refine_by_transpositions(
                left_graph, right_graph, spectral
            )
            graph_score = graph_agreement(left_graph, right_graph, refined)
            rng = np.random.default_rng(args.seed + 100000 + midpoint + window)
            graph_null = np.asarray(
                [
                    graph_agreement(left_graph, right_graph, rng.permutation(circuit.n_qubits))
                    for _ in range(args.null_trials)
                ]
            )
            graph_significance = assignment_significance(graph_score, graph_null)
            mismatch_stop = min(axis_count, midpoint + 2 * window)
            mismatch_right = graph_fn(circuit, mismatch_stop, min(axis_count, mismatch_stop + window))
            mismatch_permutation = spectral_assignment(left_graph, mismatch_right)
            mismatch_score = graph_agreement(left_graph, mismatch_right, mismatch_permutation)
            shuffled_rng = np.random.default_rng(args.seed + 200000 + midpoint + window)
            shuffled_two_qubit = list(circuit.two_qubit)
            shuffled_rng.shuffle(shuffled_two_qubit)
            shuffled = replace(circuit, two_qubit=tuple(shuffled_two_qubit))
            shuffled_left = fingerprint_fn(shuffled, midpoint - window, midpoint)
            shuffled_right = fingerprint_fn(
                shuffled, midpoint, midpoint + window, reverse=True
            )
            shuffled_score = hungarian(compatibility(shuffled_left, shuffled_right)).score
            records.append(
                {
                    "midpoint_index": midpoint,
                    "window": window,
                    "assignment_score": assignment.score,
                    "null_mean": significance["null_mean"],
                    "null_std": significance["null_std"],
                    "z": significance["z"],
                    "empirical_p": significance["empirical_p"],
                    "permutation": list(assignment.permutation),
                    "median_assignment_margin": float(np.median(assignment.margins)),
                    "graph_score": graph_score,
                    "graph_null_mean": graph_significance["null_mean"],
                    "graph_null_std": graph_significance["null_std"],
                    "graph_z": graph_significance["z"],
                    "graph_empirical_p": graph_significance["empirical_p"],
                    "graph_refinement_history": refinement_history,
                "graph_permutation": list(int(value) for value in refined),
                "mismatched_window_graph_score": mismatch_score,
                "shuffled_layer_temporal_score": shuffled_score,
                "null_control_note": "random-permutation scores use fixed random mappings; optimized matching score is not a fair optimized-null significance test",
                }
            )
    records.sort(key=lambda row: row["assignment_score"], reverse=True)
    best_by_window = {}
    for window in args.windows:
        best_by_window[str(window)] = max(
            (row for row in records if row["window"] == window), key=lambda row: row["graph_score"]
        )
    permutations = [np.asarray(row["graph_permutation"]) for row in best_by_window.values()]
    stability = (
        float(
            np.mean(
                [
                    np.mean(permutations[i] == permutations[j])
                    for i in range(len(permutations))
                    for j in range(i + 1, len(permutations))
                ]
            )
        )
        if len(permutations) > 1
        else 1.0
    )
    result = {
        "schema": "hqap-structural-analysis-v1",
        "label": args.label,
        "qasm": str(args.qasm),
        "qasm_sha256": __import__("hashlib").sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": circuit.n_qubits,
        "n_events": len(circuit.events),
        "n_two_qubit": circuit.n_two_qubit,
        "axis": args.axis,
        "search": {
            "center": center,
            "radius": args.radius,
            "step": args.step,
            "windows": args.windows,
            "null_trials": args.null_trials,
            "seed": args.seed,
        },
        "best_by_window": best_by_window,
        "neighboring_window_permutation_stability": stability,
        "best_overall": records[0],
        "records": records,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    with (args.output / "midpoint_scores.csv").open("w", newline="") as handle:
        fields = [
            "midpoint_index",
            "window",
            "assignment_score",
            "null_mean",
            "null_std",
            "z",
            "empirical_p",
            "median_assignment_margin",
            "graph_score",
            "graph_null_mean",
            "graph_null_std",
            "graph_z",
            "graph_empirical_p",
            "mismatched_window_graph_score",
            "shuffled_layer_temporal_score",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in fields} for row in records)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    for window in args.windows:
        subset = [row for row in records if row["window"] == window]
        subset.sort(key=lambda row: row["midpoint_index"])
        axis.plot(
            [row["midpoint_index"] for row in subset],
            [row["graph_z"] for row in subset],
            marker="o",
            label=f"W={window}",
        )
    axis.axhline(5, color="black", linestyle="--", linewidth=0.8, label="5 sigma")
    axis.set(
        xlabel=f"Candidate midpoint ({args.axis} index)",
        ylabel="Graph agreement z vs random-permutation null",
        title=f"{args.label} mirror structural signal",
    )
    axis.legend()
    figure.tight_layout()
    figure.savefig(args.output / "match_vs_null.png", dpi=220)
    plt.close(figure)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--axis", choices=["q2", "layer"], default="q2")
    parser.add_argument("--radius", type=int, default=128)
    parser.add_argument("--step", type=int, default=32)
    parser.add_argument("--windows", type=int, nargs="+", default=[64, 128, 256])
    parser.add_argument("--null-trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    print(json.dumps(analyze(args)["best_by_window"], indent=2))


if __name__ == "__main__":
    main()
