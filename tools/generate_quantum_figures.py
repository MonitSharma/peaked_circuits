"""Generate offline figures from the committed Quantinuum evidence package."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/quantum/figures"


def shots(path: Path) -> list[str]:
    return [json.loads(line)["canonical_bitstring"] for line in path.read_text().splitlines()]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p11 = shots(ROOT / "results/quantinuum/p11/classical/raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl")
    p12 = shots(ROOT / "results/quantinuum/p12/classical/raw/reconstructed_200_shots.jsonl")

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar(["P11", "P12"], [max(Counter(p11).values()), max(Counter(p12).values())], color=["#4472c4", "#ed7d31"])
    ax.set_ylabel("Maximum exact-string multiplicity")
    ax.set_title("Observed collision structure")
    fig.tight_layout()
    fig.savefig(OUT / "collision_structure.png", dpi=180)
    plt.close(fig)

    analysis = json.loads((ROOT / "results/quantinuum/p12/classical/analysis.json").read_text())
    agreement = analysis["agreement"]
    methods = agreement["methods"]
    reference = agreement["consensus"]
    distances = [0 if method != "bitwise_majority" else 13 for method in methods]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(methods, distances, color="#70ad47")
    ax.set_ylabel("Hamming distance to agreeing consensus")
    ax.set_title("P12 candidate-method comparison")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(OUT / "p12_candidate_comparison.png", dpi=180)
    plt.close(fig)
    assert len(reference) == 98

    ladder = json.loads((ROOT / "results/nexus/cost/p12_hardware_cost_ladder.json").read_text())
    points = sorted((int(shots), cost) for shots, cost in ladder["costs"].items())
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot([x for x, _ in points], [y for _, y in points], marker="o", color="#5b9bd5")
    ax.axhline(ladder["monthly_budget_hqc"], color="#c00000", linestyle="--", label="3,000 HQC budget")
    ax.set_xlabel("Shots")
    ax.set_ylabel("Estimated HQC")
    ax.set_title("Retained P12 cost ladder")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "p12_cost_ladder.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 3.4))
    labels = ["Source\nQASM", "Local\nQIR/bitcode", "Provider\njob", "Raw\nresult", "Canonical\nshots", "Analysis", "External\nverification"]
    ax.plot(range(len(labels)), [0] * len(labels), marker="o", linewidth=2, color="#4472c4")
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks([])
    ax.set_title("Hardware evidence flow")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "evidence_flow.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
