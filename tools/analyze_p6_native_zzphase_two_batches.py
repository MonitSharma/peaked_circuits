#!/usr/bin/env python3
"""Analyze and compare the two independent 50-shot native-ZZPhase P6 batches."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from p12_recovery.recovery import bitwise_majority_string, cluster_consensus, method_agreement, most_frequent_string, weighted_observed_medoid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/hardware/p6_optimized_compile_20260907"
QUBITS = 62
METHODS = [most_frequent_string, bitwise_majority_string, weighted_observed_medoid, cluster_consensus]


def reconstruct(path: Path) -> tuple[list[str], dict[str, object]]:
    raw = path.read_text()
    records = [(label, int(value)) for value, label in re.findall(r"OUTPUT\tRESULT\t([01])\t(m\d{3})\[0\]", raw)]
    frames: list[str] = []
    for offset in range(0, len(records), QUBITS):
        frame = dict(records[offset : offset + QUBITS])
        if len(frame) == QUBITS and all(f"m{i:03d}" in frame for i in range(QUBITS)):
            frames.append("".join(str(frame[f"m{i:03d}"]) for i in range(QUBITS)))
    return frames[:50], {
        "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "measurement_records": len(records),
        "reconstructed_frames": len(frames),
        "provider_reported_shots": 50,
        "analysis_frames_used": min(50, len(frames)),
        "extra_reconstructed_frames_excluded": max(0, len(frames) - 50),
        "start_markers": raw.count("START"),
        "end_markers": raw.count("END"),
    }


def decode(shots: list[str]) -> dict[str, object]:
    counts = Counter(shots)
    candidates = [f(counts) for f in METHODS]
    return {
        "shot_count": len(shots),
        "unique_strings": len(counts),
        "top_counts": [{"bitstring": s, "count": n} for s, n in counts.most_common(10)],
        "candidates": [c.model_dump(mode="json") for c in candidates],
        "method_agreement": method_agreement(candidates),
    }


def by_method(decoded: dict[str, object]) -> dict[str, str]:
    return {c["method_name"]: c["canonical_bitstring"] for c in decoded["candidates"]}  # type: ignore[index]


def ham(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b, strict=True))


def main() -> int:
    paths = [
        BASE / "native_zzphase_50shot/raw_result.json",
        BASE / "native_zzphase_50shot_batch2/raw_result.json",
    ]
    decoded = []
    framing = []
    for path in paths:
        shots, frame_info = reconstruct(path)
        decoded.append(decode(shots))
        framing.append(frame_info)
    pooled_shots = []
    for path in paths:
        pooled_shots.extend(reconstruct(path)[0])
    pooled = decode(pooled_shots)
    first, second = by_method(decoded[0]), by_method(decoded[1])
    comparison = {method: ham(first[method], second[method]) for method in first}
    report = {
        "schema_version": "p6-native-zzphase-two-batch-analysis-v1",
        "independent_batches": decoded,
        "framing": framing,
        "same_qir_sha256": "494b1003132a910ca0a4f39bbb41f258561d4f7091f8d495fcd8f94e4f09c851",
        "candidate_hamming_batch1_vs_batch2": comparison,
        "pooled_100_shots": pooled,
        "interpretation": {
            "target_blind": True,
            "pooled_only_after_independent_analysis": True,
            "previous_500_shot_pool_included": False,
            "warning": "Decoder summaries are exploratory and do not establish reproducible recovery.",
        },
    }
    out = BASE / "native_zzphase_two_batch_analysis.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# P6 native-ZZPhase two-batch analysis", "", "The two independent 50-shot runs used identical native-ZZPhase bitcode and were analyzed separately before pooling.", ""]
    for i, item in enumerate(decoded, 1):
        lines += [f"## Batch {i}", "", f"- Shots analyzed: **{item['shot_count']}**", f"- Unique strings: **{item['unique_strings']}**", "", "| Method | Candidate |", "|---|---|"]
        for method, value in by_method(item).items():
            lines.append(f"| {method} | `{value}` |")
        lines.append("")
    lines += ["## Cross-batch decoder distance", "", "| Method | Hamming distance |", "|---|---:|"]
    lines += [f"| {method} | {distance} |" for method, distance in comparison.items()]
    lines += ["", "## Pooled 100-shot summary", "", f"- Unique strings: **{pooled['unique_strings']}**", "", "| Method | Candidate |", "|---|---|"]
    for method, value in by_method(pooled).items():
        lines.append(f"| {method} | `{value}` |")
    lines += ["", "The pooled result is exploratory only and remains separate from the earlier 500-shot campaign.", ""]
    (BASE / "native_zzphase_two_batch_analysis.md").write_text("\n".join(lines))
    print(json.dumps({"batch1_vs_batch2_hamming": comparison, "pooled": by_method(pooled)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
