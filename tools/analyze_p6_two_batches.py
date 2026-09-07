#!/usr/bin/env python3
"""Analyze P6 discovery batches independently, then pool reported frames."""
from __future__ import annotations

import hashlib
import json
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
OUT = ROOT / "results/hardware/p6_helios_two_batch_analysis_20260907"


def reconstruct(path: Path) -> tuple[list[str], dict[str, int | str]]:
    raw = path.read_text()
    records = [(label, int(value)) for value, label in re.findall(r"OUTPUT\tRESULT\t([01])\t(m\d{3})\[0\]", raw)]
    shots: list[str] = []
    for offset in range(0, len(records), 62):
        frame = dict(records[offset : offset + 62])
        if len(frame) == 62:
            shots.append("".join(str(frame[f"m{index:03d}"]) for index in range(62)))
    return shots, {
        "provider_reported_shots": 100,
        "measurement_records": len(records),
        "reconstructed_frames": len(shots),
        "end_markers": raw.count("END"),
        "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
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
        "top_counts": counts.most_common(10),
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        "method_agreement": method_agreement(candidates),
    }


def hamming(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right, strict=True))


def candidate(candidates: list[dict[str, object]], method: str) -> str:
    return next(item["canonical_bitstring"] for item in candidates if item["method_name"] == method)  # type: ignore[return-value]


def main() -> int:
    batch1, framing1 = reconstruct(RAW1)
    batch2, framing2 = reconstruct(RAW2)
    first1, first2 = batch1[:100], batch2[:100]
    d1, d2, pooled = decode(first1), decode(first2), decode(first1 + first2)
    mode1, mode2 = candidate(d1["candidates"], "most_frequent"), candidate(d2["candidates"], "most_frequent")  # type: ignore[arg-type]
    prior = {
        "original_mettleq_34_of_62": "11011011110101011010100010111011001100010100000011100001110010",
        "circuitpermmps_d128_seed789": "10001000011000101110100011011010110011010011111000100100011000",
        "best_score_constrained_40_of_62": "10101111111011011111110000011010110011000101000101101111111000",
    }
    comparison = {
        "batch1_mode_vs_batch2_mode_hamming": hamming(mode1, mode2),
        "batch1_mode_vs_prior": {name: hamming(mode1, value) for name, value in prior.items()},
        "batch2_mode_vs_prior": {name: hamming(mode2, value) for name, value in prior.items()},
        "prior_recorded_overlaps": {"original_mettleq_34_of_62": "34/62", "best_score_constrained_40_of_62": "40/62"},
        "external_scores_used_for_selection": False,
    }
    payload = {
        "schema_version": "p6-two-discovery-batches-v1",
        "batch_1_framing": framing1,
        "batch_2_framing": framing2,
        "batch_1_first_100": d1,
        "batch_2_first_100": d2,
        "pooled_first_200": pooled,
        "comparison": comparison,
        "interpretation": "Analyze each batch independently before pooling; no confirmation candidate was assumed.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"batch1_mode": mode1, "batch2_mode": mode2, **comparison}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
