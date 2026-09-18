#!/usr/bin/env python3
"""Generate auditable recovery diagnostics for the P11/P12 packages."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "results" / "tracker_submissions"
CONFIG = {
    "p11": (
        "classical/raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl",
        "10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000",
        "P11 Helios-1: observed frequency and candidate distances",
    ),
    "p12": (
        "classical/raw/reconstructed_200_shots.jsonl",
        "10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100",
        "P12 Helios-1: observed frequency and candidate distances",
    ),
}


def hamming(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right, strict=True))


def generate(name: str, shot_file: str, answer: str, title: str) -> None:
    package = ROOT / name
    shots = [json.loads(line)["canonical_bitstring"] for line in (package / shot_file).read_text().splitlines() if line.strip()]
    counts = Counter(shots)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:15]
    distances = [hamming(shot, answer) for shot in shots]
    agreement_by_position = [
        sum(shot[position] == answer[position] for shot in shots) / len(shots)
        for position in range(len(answer))
    ]

    figure, axes = plt.subplots(2, 2, figsize=(13, 9), gridspec_kw={"height_ratios": [1, 1.05]})
    figure.suptitle(title, fontsize=15, fontweight="bold")
    frequency_axis, distance_axis = axes[0]
    agreement_axis = axes[1, 0]
    summary_axis = axes[1, 1]

    ranks = np.arange(1, len(ranked) + 1)
    frequencies = [count for _, count in ranked]
    frequency_axis.bar(ranks, frequencies, color="#2f6f9f", edgecolor="#173b58", linewidth=0.5)
    frequency_axis.set_title("Exact-string frequency")
    frequency_axis.set_xlabel("Observed-string rank")
    frequency_axis.set_ylabel("Frequency (shots)")
    frequency_axis.set_xticks(ranks)
    frequency_axis.grid(axis="y", alpha=0.25)
    frequency_axis.text(
        0.02, 0.94, f"n = {len(shots)}; unique = {len(counts)}",
        transform=frequency_axis.transAxes, va="top", fontsize=10,
    )
    for rank, count in zip(ranks, frequencies, strict=True):
        frequency_axis.text(rank, count + 0.03, str(count), ha="center", va="bottom", fontsize=9)

    distance_axis.hist(
        distances,
        bins=np.arange(min(distances) - 0.5, max(distances) + 1.5, 1),
        color="#c56a2d", edgecolor="#743d1e", linewidth=0.5,
    )
    distance_axis.axvline(np.median(distances), color="#7b1fa2", linestyle="--", linewidth=1.5, label=f"median = {np.median(distances):.0f}")
    distance_axis.set_title("Hamming distance to recovered string")
    distance_axis.set_xlabel("Hamming distance (bits)")
    distance_axis.set_ylabel("Frequency (shots)")
    distance_axis.grid(axis="y", alpha=0.25)
    distance_axis.legend(frameon=False, loc="upper left")

    positions = np.arange(1, len(answer) + 1)
    agreement_axis.plot(positions, agreement_by_position, color="#2e7d32", linewidth=1.5)
    agreement_axis.fill_between(positions, agreement_by_position, 0.5, color="#81c784", alpha=0.25)
    agreement_axis.axhline(0.5, color="#666666", linestyle=":", linewidth=1)
    agreement_axis.set_title("Per-bit agreement with recovered string")
    agreement_axis.set_xlabel("Bit position")
    agreement_axis.set_ylabel("Agreement across shots")
    agreement_axis.set_ylim(0, 1.02)
    agreement_axis.grid(axis="y", alpha=0.25)

    summary_axis.axis("off")
    summary_axis.text(0.02, 0.92, "Dataset summary", fontsize=12, fontweight="bold", transform=summary_axis.transAxes)
    summary_axis.text(
        0.02, 0.76,
        f"Shots analyzed\n{len(shots)}\n\nUnique strings\n{len(counts)}\n\nMean Hamming distance\n{np.mean(distances):.2f} bits\n\nExact recovered-string hits\n{sum(distance == 0 for distance in distances)}",
        transform=summary_axis.transAxes, va="top", fontsize=11, linespacing=1.45,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.96))
    output = package / "figures" / "frequency_and_distance.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(figure)
    print(f"wrote {output} ({len(shots)} shots, {len(counts)} unique strings)")


if __name__ == "__main__":
    for package_name, (shot_file, answer, title) in CONFIG.items():
        generate(package_name, shot_file, answer, title)
