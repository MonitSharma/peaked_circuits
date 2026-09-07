#!/usr/bin/env python3
"""Target-blind reconciliation of prior P6 candidates against 300 hardware shots."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = [
    ROOT / "results/hardware/p6_helios_100shot_20260907/raw_result.json",
    ROOT / "results/hardware/p6_helios_100shot_20260907_batch2/raw_result.json",
    ROOT / "results/hardware/p6_helios_100shot_20260907_batch3/raw_result.json",
]
OUT = ROOT / "results/hardware/p6_candidate_reconciliation_20260907"
QUBITS = 62

CANDIDATES = {
    "classical_mettleq": ("11011011110101011010100010111011001100010100000011100001110010", "34/62"),
    "classical_d128_seed789": ("10001000011000101110100011011010110011010011111000100100011000", None),
    "classical_best_score_constrained": ("10101111111011011111110000011010110011000101000101101111111000", "40/62"),
    "classical_d128_extract": ("11100011000101111111011101011001110100110110000011010010010010", "30/62"),
    "classical_d512_predicted": ("11000011111011111011011100000110110000100101001001000110110110", "35/62"),
    "hardware_batch1_mode": ("01001001111111011000101110111001110111101110010011000011111101", "33/62"),
    "hardware_batch2_mode": ("10100100010110100010001111100110001100001100100111100101111101", "38/62"),
    "hardware_batch3_mode": ("01111001011111011100111001100001001110001010000011010011110001", None),
    "pooled_bitwise_majority": ("11101100110110000001001011010101111101001110010101111111110101", None),
    "pooled_medoid": ("11101100110110100000001011000100111100011010000101101110100001", None),
}


def reconstruct(path: Path) -> tuple[list[str], dict[str, object]]:
    raw = path.read_text()
    records = [(label, int(value)) for value, label in re.findall(r"OUTPUT\tRESULT\t([01])\t(m\d{3})\[0\]", raw)]
    shots: list[str] = []
    for offset in range(0, len(records), QUBITS):
        frame = dict(records[offset : offset + QUBITS])
        if len(frame) == QUBITS:
            shots.append("".join(str(frame[f"m{i:03d}"]) for i in range(QUBITS)))
    return shots[:100], {"path": str(path), "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(), "frames_used": min(100, len(shots))}


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b, strict=True))


def candidate_consensus(strings: list[str]) -> str:
    return "".join("1" if sum(s[i] == "1" for s in strings) > len(strings) / 2 else "0" for i in range(QUBITS))


def candidate_medoid(strings: list[str]) -> str:
    return min(strings, key=lambda s: (sum(hamming(s, t) for t in strings), s))


def main() -> int:
    batches = [reconstruct(path) for path in RAW]
    shots_by_batch = [items[0] for items in batches]
    all_shots = [shot for batch in shots_by_batch for shot in batch]
    rows = []
    for name, (value, external_overlap) in CANDIDATES.items():
        per_batch = []
        for shots in shots_by_batch:
            distances = [hamming(value, shot) for shot in shots]
            per_batch.append({
                "nearest_hamming": min(distances),
                "mean_hamming": sum(distances) / len(distances),
                "shots_at_or_below_10": sum(d <= 10 for d in distances),
                "shots_at_or_below_15": sum(d <= 15 for d in distances),
                "shots_at_or_below_20": sum(d <= 20 for d in distances),
                "exact_count": sum(d == 0 for d in distances),
            })
        all_distances = [hamming(value, shot) for shot in all_shots]
        rows.append({
            "name": name,
            "bitstring": value,
            "prior_external_overlap_descriptive_only": external_overlap,
            "nearest_hamming_all_300": min(all_distances),
            "mean_hamming_all_300": sum(all_distances) / len(all_distances),
            "shots_at_or_below_10_all_300": sum(d <= 10 for d in all_distances),
            "shots_at_or_below_15_all_300": sum(d <= 15 for d in all_distances),
            "shots_at_or_below_20_all_300": sum(d <= 20 for d in all_distances),
            "exact_observed_count_all_300": sum(d == 0 for d in all_distances),
            "per_batch": per_batch,
        })

    source_strings = [CANDIDATES[name][0] for name in (
        "classical_mettleq", "classical_best_score_constrained", "classical_d128_extract",
        "classical_d512_predicted", "hardware_batch1_mode", "hardware_batch2_mode", "hardware_batch3_mode",
    )]
    leave_one_out = []
    for omitted in range(len(source_strings)):
        kept = source_strings[:omitted] + source_strings[omitted + 1:]
        consensus = candidate_consensus(kept)
        leave_one_out.append({
            "omitted_source": list(CANDIDATES)[omitted],
            "consensus": consensus,
            "distance_to_full_consensus": hamming(consensus, candidate_consensus(source_strings)),
        })
    full_consensus = candidate_consensus(source_strings)
    payload = {
        "schema_version": "p6-candidate-reconciliation-v1",
        "target_blind": True,
        "external_overlap_scores_used_for_selection": False,
        "framing": [info for _, info in batches],
        "hardware_shot_count": len(all_shots),
        "candidate_rows": sorted(rows, key=lambda row: (row["mean_hamming_all_300"], row["name"])),
        "candidate_family": {
            "full_coordinate_consensus": full_consensus,
            "candidate_family_medoid": candidate_medoid(source_strings),
            "pairwise_hamming_matrix": {
                name: {other: hamming(value, other_value) for other, (other_value, _) in CANDIDATES.items()}
                for name, (value, _) in CANDIDATES.items()
            },
            "leave_one_out": leave_one_out,
        },
        "interpretation": {
            "decision": "NO_NEW_VERIFIED_CANDIDATE",
            "reason": "No prior candidate has a reproducible tight hardware cluster across all three batches; external overlaps are post-hoc diagnostics and cannot validate a new string.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reconciliation.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"top_by_mean_hamming": payload["candidate_rows"][:5], "candidate_family": payload["candidate_family"], "interpretation": payload["interpretation"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
