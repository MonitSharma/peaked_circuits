#!/usr/bin/env python3
"""Generate auditable frequency and distance plots for tracker packages."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


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
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    distances = [hamming(shot, answer) for shot in shots]

    figure, (frequency_axis, distance_axis) = plt.subplots(1, 2, figsize=(13, 5.5))
    figure.suptitle(title, fontsize=13)
    frequency_axis.bar([str(i) for i in range(1, len(ranked) + 1)], [count for _, count in ranked], color="#2f6f9f")
    frequency_axis.set_title("Top 20 observed strings")
    frequency_axis.set_xlabel("Rank (ties lexicographically ordered)")
    frequency_axis.set_ylabel("Frequency (shots)")
    frequency_axis.grid(axis="y", alpha=0.25)
    frequency_axis.text(0.02, 0.96, f"n = {len(shots)}; unique = {len(counts)}", transform=frequency_axis.transAxes, va="top")
    distance_axis.hist(distances, bins=range(min(distances), max(distances) + 2), align="left", rwidth=0.85, color="#c56a2d")
    distance_axis.set_title("Distance to recovered candidate")
    distance_axis.set_xlabel("Hamming distance (bits)")
    distance_axis.set_ylabel("Frequency (shots)")
    distance_axis.grid(axis="y", alpha=0.25)
    distance_axis.text(0.02, 0.96, "Candidate fixed before plotting", transform=distance_axis.transAxes, va="top")
    figure.tight_layout()
    output = package / "figures" / "frequency_and_distance.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    print(f"wrote {output} ({len(shots)} shots, {len(counts)} unique strings)")


if __name__ == "__main__":
    for package_name, (shot_file, answer, title) in CONFIG.items():
        generate(package_name, shot_file, answer, title)

