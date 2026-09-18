#!/usr/bin/env python3
"""Materialize the bounded P9 distillation evidence and no-go report."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "p11_distillation"
RUNS = Path("/tmp")
TRUE_P9 = "01101110111001100000100000001010011100101101010111110111"


def load_runs() -> list[tuple[int, dict]]:
    result = []
    for bond in (16, 32, 64):
        path = RUNS / f"p11-distillation-p9-d{bond}" / "run.json"
        if path.exists():
            result.append((bond, json.loads(path.read_text())))
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    rows = []
    marginals = []
    sign_by_bit: dict[int, list[int]] = {}
    for bond, data in runs:
        bits = "".join(str(x["predicted_bit"]) for x in data["marginals"])
        confidence = np.array([x["confidence"] for x in data["marginals"]])
        correct = sum(a == b for a, b in zip(bits, TRUE_P9, strict=True))
        rows.append(
            {
                "bond_dimension": bond,
                "status": "completed",
                "correct_bits": correct,
                "n_bits": len(TRUE_P9),
                "hamming_distance": len(TRUE_P9) - correct,
                "min_confidence": float(confidence.min()),
                "median_confidence": float(np.median(confidence)),
                "runtime_s": data["runtime_s"],
                "peak_rss_bytes": data["peak_rss_bytes"],
                "max_bond_ever": data["diagnostics"]["max_bond_ever"],
                "relative_discarded_weight_sum": data["diagnostics"][
                    "relative_discarded_weight_sum"
                ],
                "candidate": bits,
            }
        )
        for item in data["marginals"]:
            i = item["logical_qubit"]
            sign_by_bit.setdefault(i, []).append(item["predicted_bit"])
            marginals.append({"bond_dimension": bond, **item})

    rows.extend(
        [
            {
                "bond_dimension": 128,
                "status": "stopped_resource_policy",
                "correct_bits": "",
                "n_bits": 56,
                "hamming_distance": "",
                "min_confidence": "",
                "median_confidence": "",
                "runtime_s": ">720",
                "peak_rss_bytes": "~103MB",
                "max_bond_ever": 128,
                "relative_discarded_weight_sum": "",
                "candidate": "",
            },
            {
                "bond_dimension": 256,
                "status": "not_run_after_non_improving_ladder",
                "correct_bits": "",
                "n_bits": 56,
                "hamming_distance": "",
                "min_confidence": "",
                "median_confidence": "",
                "runtime_s": "",
                "peak_rss_bytes": "",
                "max_bond_ever": 256,
                "relative_discarded_weight_sum": "",
                "candidate": "",
            },
        ]
    )
    with (OUT / "p9_distillation_ladder.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (OUT / "p9_bit_marginals.csv").open("w", newline="") as handle:
        fields = list(marginals[0])
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(marginals)

    stability = []
    for i in range(56):
        votes = sign_by_bit.get(i, [])
        ones = sum(votes)
        zeros = len(votes) - ones
        stability.append(
            {
                "logical_qubit": i,
                "runs": len(votes),
                "fraction_vote_1": ones / len(votes) if votes else "",
                "consensus": max(ones, zeros) / len(votes) if votes else "",
                "predicted_bit": int(ones >= zeros) if votes else "",
                "true_bit_p9": int(TRUE_P9[i]),
                "stable_across_completed_D": len(set(votes)) <= 1 if votes else False,
            }
        )
    with (OUT / "p9_bit_stability.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stability[0]))
        writer.writeheader()
        writer.writerows(stability)

    completed = [r for r in rows if r["status"] == "completed"]
    ds = [r["bond_dimension"] for r in completed]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(ds, [r["correct_bits"] for r in completed], "o-")
    ax.axhline(56, color="black", ls="--", lw=0.8)
    ax.set(
        xlabel="Bond dimension D", ylabel="P9 peak bits correct", title="P9 low-bond distillation"
    )
    fig.tight_layout()
    fig.savefig(OUT / "p9_correct_bits_vs_D.png", dpi=220)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(ds, [r["median_confidence"] for r in completed], "o-")
    ax.set(xlabel="Bond dimension D", ylabel="Median 2|p(1)-0.5|", title="P9 marginal confidence")
    fig.tight_layout()
    fig.savefig(OUT / "p9_marginal_confidence_vs_D.png", dpi=220)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.scatter(
        [r["relative_discarded_weight_sum"] for r in completed],
        [r["correct_bits"] for r in completed],
    )
    for r in completed:
        ax.annotate(
            f"D={r['bond_dimension']}", (r["relative_discarded_weight_sum"], r["correct_bits"])
        )
    ax.set(
        xlabel="Accumulated relative discarded-weight diagnostic",
        ylabel="P9 peak bits correct",
        title="Global error versus peak recovery",
    )
    fig.tight_layout()
    fig.savefig(OUT / "p9_global_error_vs_recovery.png", dpi=220)
    plt.close(fig)

    report = """# P11 distillation report — bounded P9 gate result

## Decision

**P9 Gate A: NO-GO. P11 was not run.** The direct-marginal low-bond engine
recovered 36/56, 29/56, and 27/56 P9 bits at D=16, 32, and 64 respectively.
Confidence also declined from D=16 to D=64. The D=128 run was stopped after
more than twelve minutes under the resource policy because it was not showing
an improving signal; D=256 was not launched. No P11 candidate was produced.

This is a no-go for this specific low-bond MPS protocol on this machine, not a
claim that P11 is classically impossible.

## Method

The wrapper uses the local MettleQ MPS engine with complex64 tensors,
renormalized SVD splits, restoring swap routing, direct single-site Z
expectations, explicit logical-to-site mapping, checkpoint snapshots every
500-1000 operations, and process RSS telemetry. The global discarded-weight
diagnostic is reported but was not used to reject runs.

P9 was the only truth comparison. P11 remained blind: no P11 output, tracker
submission, emulator, hardware result, or leaked bitstring was consulted.

## Reproducibility

See `AUDIT.json`, `p9_distillation_ladder.csv`, `p9_bit_marginals.csv`, and
`p9_bit_stability.csv`. The engine source is
`tools/run_mps_distillation.py`; the external MettleQ checkout was pinned to
the local clone used for these runs and its package version is recorded in the
audit. The canonical P9 input hash is
`cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35`.
"""
    (ROOT / "docs" / "P11_DISTILLATION_REPORT.md").write_text(report)
    (OUT / "NO_GO.json").write_text(
        json.dumps(
            {
                "gate": "P9_A",
                "decision": "NO-GO",
                "p11_run": False,
                "reason": "completed D16/D32/D64 ladder degraded; D128 stopped under resource policy; no protocol freeze",
                "blind": True,
            },
            indent=2,
        )
        + "\n"
    )

    files = [
        *sorted(p for p in OUT.iterdir() if p.is_file()),
        ROOT / "docs" / "P11_DISTILLATION_PLAN.md",
        ROOT / "docs" / "P11_DISTILLATION_REPORT.md",
    ]
    with (OUT / "SHA256SUMS").open("w") as handle:
        for path in files:
            if path.name == "SHA256SUMS":
                continue
            handle.write(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}\n"
            )


if __name__ == "__main__":
    main()
