#!/usr/bin/env python3
"""Decode and analyze the independent 50-shot native-ZZPhase P6 result."""
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
RAW = ROOT / "results/hardware/p6_optimized_compile_20260907/native_zzphase_50shot/raw_result.json"
OUT = ROOT / "results/hardware/p6_optimized_compile_20260907/native_zzphase_50shot"
QUBITS = 62


def reconstruct(raw: str) -> tuple[list[str], dict[str, object]]:
    records = [(label, int(value)) for value, label in re.findall(r"OUTPUT\tRESULT\t([01])\t(m\d{3})\[0\]", raw)]
    shots: list[str] = []
    for offset in range(0, len(records), QUBITS):
        frame = dict(records[offset : offset + QUBITS])
        if len(frame) == QUBITS and all(f"m{i:03d}" in frame for i in range(QUBITS)):
            shots.append("".join(str(frame[f"m{i:03d}"]) for i in range(QUBITS)))
    return shots, {
        "measurement_records": len(records),
        "reconstructed_frames": len(shots),
        "start_markers": raw.count("START"),
        "end_markers": raw.count("END"),
    }


def main() -> int:
    raw = RAW.read_text()
    reconstructed, framing = reconstruct(raw)
    provider_reported_shots = 50
    shots = reconstructed[:provider_reported_shots]
    framing["provider_reported_shots"] = provider_reported_shots
    framing["analysis_frames_used"] = len(shots)
    framing["extra_reconstructed_frames_excluded"] = max(0, len(reconstructed) - len(shots))
    counts = Counter(shots)
    candidates = [
        most_frequent_string(counts),
        bitwise_majority_string(counts),
        weighted_observed_medoid(counts),
        cluster_consensus(counts),
    ]
    decoded = {
        "schema_version": "p6-native-zzphase-50shot-analysis-v1",
        "source_raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "shot_count": len(shots),
        "unique_strings": len(counts),
        "top_counts": [{"bitstring": s, "count": n} for s, n in counts.most_common(10)],
        "framing": framing,
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "method_agreement": method_agreement(candidates),
        "interpretation": {
            "independent_experiment": True,
            "pooled_with_previous_500": False,
            "target_blind": True,
            "warning": "50 shots are exploratory; a decoder candidate is not evidence of a reproducible P6 peak.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(decoded, indent=2) + "\n")
    lines = [
        "# P6 native-ZZPhase 50-shot analysis",
        "",
        "Independent exploratory analysis of the completed native-ZZPhase Helios-1 run.",
        "",
        f"- Reconstructed shots: **{len(shots)}**",
        f"- Unique bitstrings: **{len(counts)}**",
        f"- START/END markers: **{framing['start_markers']} / {framing['end_markers']}**",
        "- Pooled with previous 500 shots: **no**",
        "",
        "## Decoder candidates",
        "",
        "| Method | Candidate |",
        "|---|---|",
    ]
    for c in candidates:
        lines.append(f"| {c.method_name} | `{c.canonical_bitstring}` |")
    lines += [
        "",
        "All 50 observations are treated as exploratory evidence. The candidate strings are decoder summaries, not a claim of a reproducible P6 peak.",
        "",
    ]
    (OUT / "analysis.md").write_text("\n".join(lines))
    print(json.dumps({"shots": len(shots), "unique_strings": len(counts), "candidates": {c.method_name: c.canonical_bitstring for c in candidates}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
