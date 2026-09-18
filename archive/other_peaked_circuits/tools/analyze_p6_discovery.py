#!/usr/bin/env python3
"""Target-blind analysis of the preserved P6 discovery payload."""
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
RAW = ROOT / "results/hardware/p6_helios_100shot_20260907/raw_result.json"
OUT = ROOT / "results/hardware/p6_helios_100shot_20260907"


def reconstruct(text: str) -> list[str]:
    records = [(label, int(value)) for value, label in re.findall(r"OUTPUT\tRESULT\t([01])\t(m\d{3})\[0\]", text)]
    shots: list[str] = []
    for offset in range(0, len(records), 62):
        frame = dict(records[offset : offset + 62])
        if len(frame) != 62:
            continue
        shots.append("".join(str(frame[f"m{index:03d}"]) for index in range(62)))
    return shots


def decode(shots: list[str]) -> dict[str, object]:
    counts = Counter(shots)
    candidates = [
        most_frequent_string(counts),
        bitwise_majority_string(counts),
        weighted_observed_medoid(counts),
        cluster_consensus(counts),
    ]
    return {
        "shots": len(shots),
        "unique_strings": len(counts),
        "top_counts": counts.most_common(10),
        "candidates": [item.model_dump(mode="json") for item in candidates],
        "method_agreement": method_agreement(candidates),
    }


def main() -> int:
    raw = RAW.read_text()
    shots = reconstruct(raw)
    first = shots[:100]
    payload = {
        "schema_version": "p6-discovery-analysis-v1",
        "raw_result_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "provider_reported_shots": 100,
        "measurement_records": len(re.findall(r"OUTPUT\tRESULT", raw)),
        "end_markers": raw.count("END"),
        "framing_anomaly": len(shots) != 100 or raw.count("END") != 100,
        "reported_100_frame_analysis": decode(first),
        "all_reconstructed_frame_analysis": decode(shots),
        "candidate_selection": {
            "candidate": "01001001111111011000101110111001110111101110010011000011111101",
            "methods": ["most_frequent", "cluster_consensus"],
            "status": "PROVISIONAL_DISCOVERY_CANDIDATE",
            "external_target_used": False,
        },
    }
    (OUT / "analysis.json").write_text(json.dumps(payload, indent=2) + "\n")
    (OUT / "canonical_shots_first100.jsonl").write_text("\n".join(first) + "\n")
    print(json.dumps(payload["candidate_selection"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
