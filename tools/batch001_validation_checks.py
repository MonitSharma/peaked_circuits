"""Offline, target-blind internal validation checks for reconstructed Batch 001."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

from p12_recovery.recovery import bitwise_majority_string


def candidate(shots: list[str]) -> str:
    return bitwise_majority_string(dict(Counter(shots))).canonical_bitstring


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b, strict=True))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    shot_path = root / "hardware_campaign/batch_001/reconstruction/reconstructed_200_shots.jsonl"
    records = [json.loads(line) for line in shot_path.read_text().splitlines()]
    shots = [record["canonical_bitstring"] for record in records]
    full = candidate(shots)
    rng = np.random.default_rng(20260826)

    split_a, split_b = candidate(shots[:100]), candidate(shots[100:])
    subsampling = {}
    for size in (50, 100, 150, 200):
        matches = []
        for _ in range(200):
            sample = rng.choice(shots, size=size, replace=False).tolist()
            matches.append(candidate(sample) == full)
        subsampling[str(size)] = {"replicates": 200, "match_probability": sum(matches) / len(matches)}

    raw_lines = (root / "hardware_campaign/batch_001/provider/raw_result.json").read_text().splitlines()
    raw_records = []
    for line in raw_lines:
        match = re.match(r"^OUTPUT\tRESULT\t([01])\t(m\d{3}\[0\])(END\t.*)?$", line)
        if match:
            raw_records.append((match.group(2), match.group(1)))
    cycles = [raw_records[index : index + 98] for index in range(0, len(raw_records), 98)]
    all_205 = ["".join(dict(cycle)[f"m{index:03d}[0]"] for index in range(98)) for cycle in cycles]
    raw_205 = candidate(all_205)
    excluded = {37, 82, 120, 165, 201}
    framing = candidate([shot for index, shot in enumerate(all_205) if index not in excluded])
    margins = [abs(2 * sum(int(shot[index]) for shot in all_205) - len(all_205)) for index in range(98)]

    baseline_candidates = []
    baseline_excluded_counts = []
    ninety_five_margin = 1.96 * (200**0.5)
    for _ in range(200):
        random_shots = ["".join(rng.integers(0, 2, 98).astype(str)) for _ in range(200)]
        baseline_candidates.append(candidate(random_shots))
        baseline_excluded_counts.append(sum(abs(2 * sum(int(shot[index]) for shot in random_shots) - 200) > ninety_five_margin for index in range(98)))

    rerun_counts = Counter(shots)
    stored = json.loads((root / "hardware_campaign/batch_001/reconstruction/reconstructed_counts.json").read_text())["counts"]
    report = {
        "candidate": full,
        "split_half": {"first_100": split_a, "second_100": split_b, "hamming_between_halves": hamming(split_a, split_b), "hamming_first_to_full": hamming(split_a, full), "hamming_second_to_full": hamming(split_b, full)},
        "framing_sensitivity": {"raw_205_candidate": raw_205, "reconstructed_200_candidate": framing, "hamming_difference": hamming(raw_205, framing), "potentially_sensitive_positions": [index for index, margin in enumerate(margins) if margin <= 5], "excluded_cycles": sorted(excluded)},
        "random_subsampling": subsampling,
        "random_baseline": {"replicates": 200, "margin_threshold_95_percent": ninety_five_margin, "observed_bits_over_threshold": sum(abs(2 * sum(int(shot[index]) for shot in shots) - 200) > ninety_five_margin for index in range(98)), "mean_random_bits_over_threshold": sum(baseline_excluded_counts) / len(baseline_excluded_counts), "max_random_bits_over_threshold": max(baseline_excluded_counts), "candidate_match_count": sum(item == full for item in baseline_candidates)},
        "independent_rerun": {"recomputed_shots": len(shots), "recomputed_counts_sha256": hashlib.sha256(json.dumps(dict(sorted(rerun_counts.items())), sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "stored_counts_equal": dict(sorted(rerun_counts.items())) == stored, "recomputed_candidate": candidate(shots)},
        "external_target_scored": False,
    }
    output = root / "hardware_campaign/batch_001/analysis/validation_checks.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"split_hamming": report["split_half"]["hamming_between_halves"], "framing_hamming": report["framing_sensitivity"]["hamming_difference"], "subsampling": report["random_subsampling"], "rerun_equal": report["independent_rerun"]["stored_counts_equal"]}, indent=2))


if __name__ == "__main__":
    main()
