#!/usr/bin/env python3
"""Recompute the target-blind core recovery statistics from packaged shots.

This deliberately uses only the standard library. It does not read a hidden
target, call a provider, or use credentials.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "results" / "tracker_submissions"
ANSWER = {
    "p11": "10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000",
    "p12": "10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100",
}
SHOT_FILE = {
    "p11": "classical/raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl",
    "p12": "classical/raw/reconstructed_200_shots.jsonl",
}


def hamming(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right, strict=True))


def recover(name: str) -> None:
    path = ROOT / name / SHOT_FILE[name]
    shots = [json.loads(line)["canonical_bitstring"] for line in path.read_text().splitlines() if line.strip()]
    if not shots or any(len(shot) != 98 or set(shot) - {"0", "1"} for shot in shots):
        raise SystemExit(f"{name}: invalid packaged shots")
    counts = Counter(shots)
    mode = min(counts, key=lambda shot: (-counts[shot], shot))
    majority = "".join(
        "1" if sum(shot[index] == "1" for shot in shots) > len(shots) / 2 else "0"
        for index in range(98)
    )
    medoid = min(
        counts,
        key=lambda candidate: (sum(hamming(candidate, shot) * weight for shot, weight in counts.items()), candidate),
    )
    answer = ANSWER[name]
    print(json.dumps({
        "package": name,
        "shots": len(shots),
        "mode": mode,
        "bitwise_majority": majority,
        "weighted_observed_medoid": medoid,
        "accepted_answer": answer,
        "medoid_matches_accepted_answer": medoid == answer,
    }, indent=2))


if __name__ == "__main__":
    for package_name in ("p11", "p12"):
        recover(package_name)

