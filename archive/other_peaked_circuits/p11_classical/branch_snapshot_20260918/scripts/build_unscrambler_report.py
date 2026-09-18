#!/usr/bin/env python3
"""Build auditable P9 structural no-go artifacts after Gate A."""
# ruff: noqa: E402

from __future__ import annotations

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

from structural.fingerprints import compatibility, window_fingerprints
from structural.qasm_events import parse_qasm

OUT = ROOT / "results" / "p11_unscrambler"
P9 = ROOT / "data" / "canonical" / "peaked_circuit_P9_Hqap_56x1917.qasm"


def main() -> None:
    summary = json.loads((OUT / "p9_structure" / "summary.json").read_text())
    large = json.loads((OUT / "p9_structure_large_windows" / "summary.json").read_text())
    layers = json.loads((OUT / "p9_structure_layers" / "summary.json").read_text())
    unitary = json.loads((OUT / "p9_unitary_mirror" / "summary.json").read_text())
    sequence = json.loads((OUT / "p9_sequence_structure" / "summary.json").read_text())
    routed = json.loads((OUT / "p9_routed_structure" / "summary.json").read_text())
    sparse = json.loads((OUT / "p9_sparse_ladder" / "summary.json").read_text())
    unitary_sequence = json.loads((OUT / "p9_unitary_sequence" / "summary.json").read_text())
    dynamic = json.loads((OUT / "p9_dynamic_tracker" / "summary.json").read_text())
    unitary_rows = [row for row in unitary["records"] if row["center_layer"] == unitary["midpoint_layer"] and not row["adjoint_right"]]
    unitary_rows.sort(key=lambda row: row["span"])
    unitary_stability = float(np.mean([np.mean(np.asarray(unitary_rows[i]["permutation"]) == np.asarray(unitary_rows[j]["permutation"])) for i in range(len(unitary_rows)) for j in range(i + 1, len(unitary_rows))])) if len(unitary_rows) > 1 else 1.0
    circuit = parse_qasm(P9)
    recovered = {
        "schema": "p9-recovered-permutations-v1",
        "gate_a": "NO-GO",
        "neighboring_window_stability": summary["neighboring_window_permutation_stability"],
        "small_windows": summary["best_by_window"],
        "large_windows": large["best_by_window"],
        "layer_windows": layers["best_by_window"],
        "layer_window_stability": layers["neighboring_window_permutation_stability"],
        "unitary_mirror": unitary["best"],
        "unitary_center_stability": unitary_stability,
        "sequence_aware": {
            "best_by_window": sequence["best_by_window"],
            "neighboring_window_stability": sequence["neighboring_window_permutation_stability"],
        },
        "routed_sequence_aware": {
            "best_by_window": routed["best_by_window"],
            "neighboring_window_stability": routed["neighboring_window_permutation_stability"],
            "routed_two_qubit_counts": routed["routed_two_qubit_counts"],
        },
        "unitary_sequence_aware": unitary_sequence,
        "dynamic_tracker": {
            "records": dynamic["records"],
            "decision": dynamic["decision"],
        },
        "interpretation": "Strong null separation without mapping stability is insufficient evidence of latent correspondence.",
    }
    (OUT / "p9_recovered_permutations.json").write_text(json.dumps(recovered, indent=2) + "\n")
    with (OUT / "p9_patch_matches.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["status", "reason"])
        writer.writeheader()
        writer.writerow({"status": "not_run", "reason": "P9 Gate A failed before patch matching"})
    (OUT / "p9_patch_equivalence_not_run.txt").write_text(
        "Patch-unitary matching was not promoted to a P9 protocol because Gate A mapping stability failed.\n"
    )
    (OUT / "p9_reduction_report.json").write_text(
        json.dumps(
            {
                "status": "NO-GO",
                "reduction_attempted": False,
                "reason": "unstable correspondence",
                "p9_reduced_qasm": None,
            },
            indent=2,
        )
        + "\n"
    )
    (OUT / "STRUCTURAL_NO_GO.json").write_text(
        json.dumps(
            {
                "gate": "P9_A",
                "decision": "NO-GO",
                "score_null_separation": "strong",
                "mapping_stability": summary["neighboring_window_permutation_stability"],
                "large_window_stability": large["neighboring_window_permutation_stability"],
                "layer_window_stability": layers["neighboring_window_permutation_stability"],
                "sequence_window_stability": sequence["neighboring_window_permutation_stability"],
                "sequence_best_z": max(row["z"] for row in sequence["best_by_window"].values()),
                "routed_sequence_window_stability": routed["neighboring_window_permutation_stability"],
                "routed_best_score": max(row["score"] for row in routed["best_by_window"].values()),
                "routed_best_mismatched_score": max(
                    row["mismatched_score"]
                    for row in routed["best_by_window"].values()
                    if row["mismatched_score"] is not None
                ),
                "sparse_side_experiment_decision": sparse["decision"],
                "sparse_completed_rows": sum(row["complete"] for row in sparse["rows"]),
                "sparse_max_retained_completed": max(
                    (row["retained_states"] for row in sparse["rows"] if row["complete"]),
                    default=0,
                ),
                "unitary_sequence_window_stability": unitary_sequence[
                    "neighboring_window_permutation_stability"
                ],
                "unitary_sequence_best_z": max(row["z"] for row in unitary_sequence["records"]),
                "dynamic_tracker_best_z": max(row["null_z"] for row in dynamic["records"]),
                "dynamic_tracker_max_coherence": max(
                    row["mean_consecutive_agreement"] for row in dynamic["records"]
                ),
                "p11_structural_recovery_started": False,
                "p11_simulation_started": False,
                "p11_blindness_preserved": True,
            },
            indent=2,
        )
        + "\n"
    )

    best = summary["best_by_window"]["128"]
    midpoint = best.get("midpoint_index", best.get("midpoint_q2_index"))
    window = best["window"]
    matrix = compatibility(
        window_fingerprints(circuit, midpoint - window, midpoint),
        window_fingerprints(circuit, midpoint, midpoint + window, reverse=True),
    )
    figure, axis = plt.subplots(figsize=(7, 6))
    axis.imshow(matrix, aspect="auto", cmap="viridis")
    axis.set(
        xlabel="Right logical qubit",
        ylabel="Left logical qubit",
        title="P9 unary fingerprint compatibility (W=128)",
    )
    figure.tight_layout()
    figure.savefig(OUT / "p9_mapping_confidence_matrix.png", dpi=220)
    plt.close(figure)

    rows = [row for row in summary["records"] if row["window"] == 128]
    rows.sort(key=lambda row: row.get("midpoint_index", row.get("midpoint_q2_index")))
    trajectory = np.asarray([row["graph_permutation"] for row in rows])
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.imshow(trajectory.T, aspect="auto", interpolation="nearest", cmap="tab20")
    axis.set(
        xlabel="Candidate midpoint order",
        ylabel="Left qubit",
        title="P9 recovered graph-matching permutation trajectory (W=128)",
    )
    figure.tight_layout()
    figure.savefig(OUT / "p9_permutation_trajectory.png", dpi=220)
    plt.close(figure)

    prior_rows = list(csv.DictReader((OUT / "unswap_prior" / "unswap_aggregate.csv").open()))
    if prior_rows:
        grouped = {}
        for row in prior_rows:
            key = (row["side"], int(row["cycle"]))
            grouped[key] = grouped.get(key, 0) + int(row["new"])
        labels = sorted(grouped)
        figure, axis = plt.subplots(figsize=(8, 4))
        axis.bar(range(len(labels)), [grouped[label] for label in labels])
        axis.set(
            xlabel="Historical cycle/side",
            ylabel="Aggregate new swaps",
            title="Historical unswap aggregate telemetry",
        )
        axis.set_xticks(
            range(len(labels)), [f"{s}:{c}" for s, c in labels], rotation=90, fontsize=6
        )
        figure.tight_layout()
        figure.savefig(OUT / "historical_unswap_frequency.png", dpi=220)
        plt.close(figure)

    report = f"""# P11 HQAP unscrambler report

## Decision: P9 Gate A NO-GO

The optimized matcher has a large advantage over fixed random permutations,
but that is not a fair optimized-null significance test because relabeling
does not change the optimum. The fair mismatched-window and shuffled-order
controls are retained. More importantly, the recovered permutations are
unstable across neighboring windows: pairwise agreement is
`{summary["neighboring_window_permutation_stability"]:.4f}` for `[64,128,256]`
and `{large["neighboring_window_permutation_stability"]:.4f}` for the larger
`[256,512,768]` refinement. Mismatched-window and shuffled-order controls are
recorded in the corresponding summary records.
An independent layer-index analysis over `[8,16,32]` layers also gives only
`{layers["neighboring_window_permutation_stability"]:.4f}` agreement.
The ordered-edge sequence matcher reaches only about
`{max(row["z"] for row in sequence["best_by_window"].values()):.2f}` sigma against
fair shuffled-order controls in this bounded search, with neighboring-window
agreement `{sequence["neighboring_window_permutation_stability"]:.4f}`. Its
best mismatched-window scores are comparable to the mirrored scores, so it
does not rescue Gate A.
Repeating the ordered-edge test after bounded P9 split/inverse and
line-routing preprocessing produces isolated high scores, but routed mapping
stability is only
`{routed["neighboring_window_permutation_stability"]:.4f}` and the best
routed mismatched-prefix score is comparable to the best mirrored score. This
is treated as routing-induced local structure, not a recovered correspondence.
The optional P9 top-K sparse-state ladder completed only the 2^12 and 2^14
retained-state runs; both had zero probability on the supervised P9 target.
The 2^16 run hit its hard 20-second bound without reaching the end of the
circuit, so the sparse branch was stopped and no P11 proposal was made.
The continuous-unitary DTW matcher reaches only
`{max(row["z"] for row in unitary_sequence["records"]):.2f}` sigma against
shuffled controls, with mapping stability
`{unitary_sequence["neighboring_window_permutation_stability"]:.4f}`; its
mismatched-window scores are equal to or higher than the mirrored scores.
The finite-horizon tracker over beam widths `[8,16,32]` also shows no
advantage over shuffled paths: the best path z-score is
`{max(row["null_z"] for row in dynamic["records"]):.2f}`, while consecutive
permutation agreement remains at most
`{max(row["mean_consecutive_agreement"] for row in dynamic["records"]):.4f}`.
The local-unitary variant reaches optimizer scores around 0.77-0.86, but its
fixed-center permutation agreement is only `{unitary_stability:.4f}` and its
random-permutation baseline has the same optimization-invariance limitation.

This fails the required conjunction of calibrated signal and stable
correspondence. The optimizer advantage is therefore not treated as evidence
of a usable latent mapping.
P11 structural recovery and all downstream reduction/simulation were not run.

## Components implemented and tested

- QASM event extraction with temporal layers and 2q indices.
- Unary temporal fingerprints and compatibility matrices.
- Hungarian assignment, spectral graph matching, bounded transposition
  refinement, and null controls.
- Ordered temporal edge-stream matching with fair shuffled-order controls.
- Construction-aware P9 split/inverse plus bounded line-routing diagnostic.
- P9-only top-K sparse-state ladder with explicit timeout and no-signal stop.
- Continuous one-qubit unitary sequence alignment with DTW null controls.
- Finite-horizon beam tracking over time-dependent permutation states.
- Finite-horizon permutation beam tracker.
- Small-patch unitary equivalence and phase-insensitive process similarity.
- Exact adjacent inverse cancellation with provenance.
- Historical unswap aggregate audit; pair identities were unavailable, so no
  pair-level prior was fabricated.

## Provenance

P9 SHA256: `{hashlib.sha256(P9.read_bytes()).hexdigest()}`\n
P11 SHA256: `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`\n
P11 answer contamination: **none**. Existing `results/p11_diagnosis`,
`results/p11_research`, and `results/p11_distillation` were not overwritten.
"""
    (ROOT / "docs" / "P11_UNSCRAMBLER_REPORT.md").write_text(report)
    files = [
        *sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS"),
        ROOT / "docs" / "P11_UNSCRAMBLER_PLAN.md",
        ROOT / "docs" / "P11_UNSCRAMBLER_REPORT.md",
    ]
    with (OUT / "SHA256SUMS").open("w") as handle:
        for path in files:
            handle.write(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}\n"
            )


if __name__ == "__main__":
    main()
