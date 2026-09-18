#!/usr/bin/env python3
"""Bounded P9 local-unitary mirror matching with null controls."""
# ruff: noqa: E402, E702

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
from structural.unitary_matching import layer_unitary_compatibility, unitary_assignment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--radius", type=int, default=16)
    parser.add_argument("--step", type=int, default=2)
    parser.add_argument("--spans", type=int, nargs="+", default=[8, 16, 32])
    parser.add_argument("--null-trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    circuit = parse_qasm(args.qasm)
    midpoint = max(event.layer for event in circuit.events) // 2
    rows = []
    for span in args.spans:
        for center in range(midpoint - args.radius, midpoint + args.radius + 1, args.step):
            left = [layer for layer in range(center - span, center) if any(event.layer == layer and event.gate == "u" for event in circuit.events)]
            right = [layer for layer in range(center, center + span) if any(event.layer == layer and event.gate == "u" for event in circuit.events)]
            length = min(len(left), len(right))
            left, right = left[-length:], right[:length]
            if not left:
                continue
            rng = np.random.default_rng(args.seed + center + span)
            for adjoint in (False, True):
                score, overlap = layer_unitary_compatibility(circuit, left, right, adjoint_right=adjoint)
                permutation, assignment_score, support = unitary_assignment(score, overlap)
                null = []
                for _ in range(args.null_trials):
                    random_perm = rng.permutation(circuit.n_qubits)
                    null.append(float(np.mean(score[np.arange(circuit.n_qubits), random_perm])))
                null = np.asarray(null)
                null_std = float(null.std(ddof=1))
                rows.append({"center_layer": center, "span": span, "adjoint_right": adjoint, "score": assignment_score, "null_mean": float(null.mean()), "null_std": null_std, "z": (assignment_score - float(null.mean())) / null_std if null_std else 0.0, "support": support, "permutation": permutation.tolist()})
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "unitary_scores.csv").open("w", newline="") as handle:
        fields = ["center_layer", "span", "adjoint_right", "score", "null_mean", "null_std", "z", "support"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows({field: row[field] for field in fields} for row in rows)
    best = {}
    for span in args.spans:
        for adjoint in (False, True):
            subset = [row for row in rows if row["span"] == span and row["adjoint_right"] == adjoint]
            if subset:
                best[f"span_{span}_adjoint_{adjoint}"] = max(subset, key=lambda row: row["score"])
    summary = {"schema": "p9-local-unitary-mirror-v1", "label": args.label, "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(), "midpoint_layer": midpoint, "spans": args.spans, "best": best, "records": rows, "null_interpretation": "random-permutation scores are fixed-mapping baselines; they are not a fair optimized-matcher significance test"}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    figure, axis = plt.subplots(figsize=(7, 4.5))
    for span in args.spans:
        for adjoint in (False, True):
            subset = sorted((row for row in rows if row["span"] == span and row["adjoint_right"] == adjoint), key=lambda row: row["center_layer"])
            if subset:
                axis.plot([row["center_layer"] for row in subset], [row["z"] for row in subset], marker="o", label=f"W={span}, adj={adjoint}")
    axis.axhline(5, color="black", linestyle="--", linewidth=0.8); axis.set(xlabel="Candidate center layer", ylabel="Unitary assignment z", title=f"{args.label} local-unitary mirror score"); axis.legend(fontsize=7); figure.tight_layout(); figure.savefig(args.output / "unitary_match_vs_null.png", dpi=220); plt.close(figure)


if __name__ == "__main__":
    main()
