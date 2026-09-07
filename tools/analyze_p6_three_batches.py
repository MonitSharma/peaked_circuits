#!/usr/bin/env python3
"""Analyze P6 discovery batches 1-3 independently, then pool 300 frames."""
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
RAW = [
    ROOT / "results/hardware/p6_helios_100shot_20260907/raw_result.json",
    ROOT / "results/hardware/p6_helios_100shot_20260907_batch2/raw_result.json",
    ROOT / "results/hardware/p6_helios_100shot_20260907_batch3/raw_result.json",
]
OUT = ROOT / "results/hardware/p6_helios_three_batch_analysis_20260907"
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
        "measurement_records": len(records),
        "reconstructed_frames": len(shots),
        "start_markers": raw.count("START"),
        "end_markers": raw.count("END"),
        "frames_used": min(100, len(shots)),
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
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "method_agreement": method_agreement(candidates),
    }


def get_candidate(decoded: dict[str, object], method: str) -> str:
    return next(c["canonical_bitstring"] for c in decoded["candidates"] if c["method_name"] == method)  # type: ignore[index]


def hamming(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right, strict=True))


def bit_stability(shots: list[str]) -> dict[str, object]:
    p1 = [sum(s[i] == "1" for s in shots) / len(shots) for i in range(QUBITS)]
    stable = [i for i, p in enumerate(p1) if p <= 0.25 or p >= 0.75]
    return {
        "threshold": "p1 <= 0.25 or p1 >= 0.75",
        "stable_position_count": len(stable),
        "stable_positions_zero_based": stable,
        "bitwise_ensemble_candidate": "".join("1" if p > 0.5 else "0" for p in p1),
        "p1_by_position": p1,
    }


def main() -> int:
    all_shots: list[list[str]] = []
    framing: list[dict[str, object]] = []
    for path in RAW:
        shots, info = reconstruct(path)
        all_shots.append(shots[:100])
        framing.append(info)
    decoded = [decode(shots) for shots in all_shots]
    pooled = [shot for batch in all_shots for shot in batch]
    pooled_decoded = decode(pooled)
    modes = [get_candidate(d, "most_frequent") for d in decoded]
    payload = {
        "schema_version": "p6-three-discovery-batches-v1",
        "target_blind": True,
        "provider_submission_performed": False,
        "framing": framing,
        "batch_1": decoded[0],
        "batch_2": decoded[1],
        "batch_3": decoded[2],
        "pooled_300": pooled_decoded,
        "mode_comparison": {
            "batch_modes": modes,
            "pairwise_hamming": [[hamming(a, b) for b in modes] for a in modes],
            "pooled_mode": get_candidate(pooled_decoded, "most_frequent"),
        },
        "bit_stability": bit_stability(pooled),
        "cross_batch_mode_recurrence": {
            "exact_mode_recurrence": len(set(modes)),
            "note": "Modes are compared descriptively; they were not used to select or target the third job.",
        },
        "interpretation": {
            "pooled_unique_strings": pooled_decoded["unique_strings"],
            "pooled_mode_count": pooled_decoded["top_counts"][0]["count"],  # type: ignore[index]
            "decision": "NO_REPRODUCIBLE_FULL_CANDIDATE",
            "reason": "The three batches do not share a recurring mode and the pooled distribution remains diffuse; pooling does not establish a complete P6 answer.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"modes": modes, "pooled": payload["interpretation"], "bit_stability": payload["bit_stability"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
