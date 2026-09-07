#!/usr/bin/env python3
"""Offline forensic analysis of the two preserved 100-shot P6 batches.

This script is deliberately target-blind: it uses only the reconstructed
hardware shots and previously frozen candidate strings.  It never contacts a
provider and never submits a job.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

from p12_recovery.recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)

ROOT = Path(__file__).resolve().parents[1]
RAW1 = ROOT / "results/hardware/p6_helios_100shot_20260907/raw_result.json"
RAW2 = ROOT / "results/hardware/p6_helios_100shot_20260907_batch2/raw_result.json"
OUT = ROOT / "results/hardware/p6_200shot_forensics_20260907"
QUBITS = 62


def reconstruct(path: Path) -> tuple[list[str], dict[str, object]]:
    raw = path.read_text()
    records = [(label, int(value)) for value, label in re.findall(r"OUTPUT\tRESULT\t([01])\t(m\d{3})\[0\]", raw)]
    shots: list[str] = []
    for offset in range(0, len(records), QUBITS):
        frame = dict(records[offset : offset + QUBITS])
        if len(frame) == QUBITS:
            shots.append("".join(str(frame[f"m{i:03d}"]) for i in range(QUBITS)))
    return shots, {
        "path": str(path),
        "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "provider_reported_shots": 100,
        "measurement_records": len(records),
        "reconstructed_frames": len(shots),
        "start_markers": raw.count("START"),
        "end_markers": raw.count("END"),
        "analysis_frames_used": min(100, len(shots)),
    }


def decode(shots: list[str]) -> dict[str, object]:
    counts = Counter(shots)
    candidates = [
        most_frequent_string(counts),
        bitwise_majority_string(counts),
        weighted_observed_medoid(counts),
        cluster_consensus(counts),
    ]
    return {
        "shot_count": len(shots),
        "unique_strings": len(counts),
        "top_counts": [{"bitstring": s, "count": n} for s, n in counts.most_common(10)],
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        "method_agreement": method_agreement(candidates),
    }


def hamming(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right, strict=True))


def candidate(decoded: dict[str, object], method: str) -> str:
    return next(
        item["canonical_bitstring"]
        for item in decoded["candidates"]  # type: ignore[index]
        if item["method_name"] == method
    )


def split_half(shots: list[str]) -> dict[str, object]:
    half = len(shots) // 2
    left, right = shots[:half], shots[half:]
    left_decoded, right_decoded = decode(left), decode(right)
    methods = ["most_frequent", "bitwise_majority", "weighted_observed_medoid", "cluster_consensus"]
    distances = {
        method: hamming(candidate(left_decoded, method), candidate(right_decoded, method))
        for method in methods
    }
    return {
        "left_shots": len(left),
        "right_shots": len(right),
        "method_hamming_left_vs_right": distances,
        "left": left_decoded,
        "right": right_decoded,
    }


def bit_stability(shots: list[str]) -> dict[str, object]:
    n = len(shots)
    p1 = [sum(shot[i] == "1" for shot in shots) / n for i in range(QUBITS)]
    stable = [i for i, p in enumerate(p1) if p <= 0.25 or p >= 0.75]
    unresolved = [i for i in range(QUBITS) if i not in stable]
    ensemble = "".join("1" if p > 0.5 else "0" for p in p1)
    return {
        "shots": n,
        "stable_threshold": "p1 <= 0.25 or p1 >= 0.75",
        "stable_positions_zero_based": stable,
        "stable_position_count": len(stable),
        "unresolved_positions_zero_based": unresolved,
        "unresolved_position_count": len(unresolved),
        "p1_by_position": p1,
        "bitwise_ensemble_candidate": ensemble,
    }


def cross_batch_nearest(left: list[str], right: list[str]) -> dict[str, object]:
    nearest_left = [min(hamming(a, b) for b in right) for a in left]
    nearest_right = [min(hamming(b, a) for a in left) for b in right]
    values = nearest_left + nearest_right
    return {
        "left_to_right_min_hamming": nearest_left,
        "right_to_left_min_hamming": nearest_right,
        "all_pairs_min": min(values),
        "all_pairs_median_nearest": sorted(values)[len(values) // 2],
        "nearest_at_or_below": {str(t): sum(v <= t for v in values) for t in (5, 10, 15, 20)},
        "note": "Nearest-neighbour counts are descriptive; they are not independent p-values.",
    }


def bootstrap_stability(shots: list[str], replicates: int = 250) -> dict[str, object]:
    """Resample shots with replacement and summarize decoder recurrence."""
    rng = random.Random(20260907)
    methods = ("most_frequent", "bitwise_majority", "weighted_observed_medoid")
    recovered: dict[str, list[str]] = {method: [] for method in methods}
    for _ in range(replicates):
        sample = [shots[rng.randrange(len(shots))] for _ in shots]
        decoded = decode(sample)
        for method in methods:
            recovered[method].append(candidate(decoded, method))
    summary: dict[str, object] = {"replicates": replicates, "seed": 20260907}
    for method, values in recovered.items():
        counts = Counter(values)
        top, top_count = counts.most_common(1)[0]
        summary[method] = {
            "distinct_recovered_candidates": len(counts),
            "most_common_candidate": top,
            "most_common_replicates": top_count,
            "most_common_fraction": top_count / replicates,
            "top_five": [{"bitstring": s, "replicates": n} for s, n in counts.most_common(5)],
        }
    return summary


def candidate_pool(decoded: dict[str, object], shots: list[str]) -> list[dict[str, object]]:
    pool = {
        "batch1_mode": "01001001111111011000101110111001110111101110010011000011111101",
        "batch2_mode": "10100100010110100010001111100110001100001100100111100101111101",
        "original_mettleq_candidate": "11011011110101011010100010111011001100010100000011100001110010",
        "circuitpermmps_d128_seed789": "10001000011000101110100011011010110011010011111000100100011000",
        "best_score_constrained_candidate": "10101111111011011111110000011010110011000101000101101111111000",
        "d128_extract_candidate": "11100011000101111111011101011001110100110110000011010010010010",
        "d512_predicted_candidate": "11000011111011111011011100000110110000100101001001000110110110",
        "pooled_bitwise_majority": candidate(decoded, "bitwise_majority"),
        "pooled_medoid": candidate(decoded, "weighted_observed_medoid"),
        "pooled_cluster_consensus": candidate(decoded, "cluster_consensus"),
    }
    return [
        {
            "name": name,
            "bitstring": value,
            "nearest_observed_hamming": min(hamming(value, shot) for shot in shots),
            "observed_exact_count": shots.count(value),
        }
        for name, value in pool.items()
    ]


def main() -> int:
    raw1, framing1 = reconstruct(RAW1)
    raw2, framing2 = reconstruct(RAW2)
    batch1, batch2 = raw1[:100], raw2[:100]
    pooled = batch1 + batch2
    decoded1, decoded2, decoded_pool = decode(batch1), decode(batch2), decode(pooled)
    payload = {
        "schema_version": "p6-200-shot-forensics-v1",
        "target_blind": True,
        "provider_submission_performed": False,
        "framing": {"batch1": framing1, "batch2": framing2},
        "batch1": decoded1,
        "batch2": decoded2,
        "pooled_200": decoded_pool,
        "split_half": {
            "batch1": split_half(batch1),
            "batch2": split_half(batch2),
            "batch1_vs_batch2": {
                "mode_hamming": hamming(candidate(decoded1, "most_frequent"), candidate(decoded2, "most_frequent")),
                "cluster_consensus_hamming": hamming(candidate(decoded1, "cluster_consensus"), candidate(decoded2, "cluster_consensus")),
            },
        },
        "bit_stability": bit_stability(pooled),
        "bootstrap_stability": bootstrap_stability(pooled),
        "cross_batch_nearest_neighbour": cross_batch_nearest(batch1, batch2),
        "candidate_pool": candidate_pool(decoded_pool, pooled),
        "interpretation": {
            "pooled_mode_count": decoded_pool["top_counts"][0]["count"],  # type: ignore[index]
            "pooled_unique_strings": decoded_pool["unique_strings"],
            "decision": "NO_REPRODUCIBLE_FULL_CANDIDATE",
            "reason": "The two batch modes differ substantially, no pooled string dominates, and decoder outputs disagree. Stable-bit and nearest-neighbour results are useful diagnostics but do not identify a complete answer.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "forensics.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["interpretation"], indent=2))
    print(json.dumps({"bit_stability": payload["bit_stability"], "cross_batch": payload["cross_batch_nearest_neighbour"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
