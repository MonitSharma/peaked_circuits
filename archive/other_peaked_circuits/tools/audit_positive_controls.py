#!/usr/bin/env python3
"""Recompute P11/P12 recovery from saved canonical shot records.

This is a local positive-control audit.  It does not submit jobs, contact a
provider, or score against a hidden target.  The accepted strings are included
only as externally supplied verification records.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from p12_recovery.counts_io import validate_canonical_bitstring
from p12_recovery.recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/quantinuum/positive_control_audit_20260907"

CONTROLS = {
    "p11": {
        "shots": ROOT / "results/quantinuum/p11/classical/raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl",
        "stored_counts": ROOT / "results/quantinuum/p11/classical/raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.counts.json",
        "accepted": "10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000",
        "job_id": "c902a6a1-0e91-48cf-b5ba-44831fcc7726",
        "requested_shots": 50,
        "note": "Saved canonical shot records were used; the provider payload had fused framing in its final section.",
    },
    "p12": {
        "shots": ROOT / "results/quantinuum/p12/classical/raw/reconstructed_200_shots.jsonl",
        "stored_counts": ROOT / "results/quantinuum/p12/classical/raw/reconstructed_counts.json",
        "accepted": "10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100",
        "job_id": "d5cba0df-a7aa-459e-ac51-8092645c059f",
        "requested_shots": 200,
        "note": "Saved 200-shot reconstruction was used; the original payload recorded 205 cycles with five excluded framing cycles.",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hamming_distance(left: str, right: str) -> int:
    if len(left) != len(right):
        raise ValueError("Hamming distance requires equal-length strings")
    return sum(a != b for a, b in zip(left, right, strict=True))


def pairwise_mean(strings: list[str]) -> float:
    if len(strings) < 2:
        return 0.0
    total = 0
    pairs = 0
    for i, left in enumerate(strings):
        for right in strings[i + 1 :]:
            total += hamming_distance(left, right)
            pairs += 1
    return total / pairs


def audit_one(name: str, cfg: dict[str, object]) -> dict[str, object]:
    shots_path = cfg["shots"]
    counts_path = cfg["stored_counts"]
    assert isinstance(shots_path, Path)
    assert isinstance(counts_path, Path)
    records = [json.loads(line) for line in shots_path.read_text().splitlines() if line.strip()]
    for index, record in enumerate(records):
        if record.get("shot_index") != index:
            raise ValueError(f"Non-contiguous shot index at {shots_path}:{index}")
        validate_canonical_bitstring(record["canonical_bitstring"])
    shots = [record["canonical_bitstring"] for record in records]
    counts = Counter(shots)
    stored = json.loads(counts_path.read_text())
    stored_counts = stored["counts"]
    accepted = str(cfg["accepted"])
    candidates = [
        most_frequent_string(counts),
        bitwise_majority_string(counts),
        weighted_observed_medoid(counts),
        cluster_consensus(counts),
    ]
    candidate_map = {item.method_name: item.canonical_bitstring for item in candidates}
    return {
        "problem": name,
        "job_id": cfg["job_id"],
        "requested_shots": cfg["requested_shots"],
        "reconstructed_shots": len(shots),
        "unique_strings": len(counts),
        "maximum_multiplicity": max(counts.values()),
        "mean_pairwise_hamming": pairwise_mean(shots),
        "shot_file_sha256": sha256(shots_path),
        "stored_counts_sha256": sha256(counts_path),
        "shot_records_contiguous": [record["shot_index"] for record in records] == list(range(len(records))),
        "counts_recomputed_match_stored": dict(sorted(counts.items())) == dict(sorted(stored_counts.items())),
        "accepted_string": accepted,
        "accepted_string_length": len(accepted),
        "method_candidates": candidate_map,
        "method_matches_accepted": {method: value == accepted for method, value in candidate_map.items()},
        "hamming_to_accepted": {method: hamming_distance(value, accepted) for method, value in candidate_map.items()},
        "method_agreement": method_agreement(candidates),
        "source_note": cfg["note"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = {name: audit_one(name, cfg) for name, cfg in CONTROLS.items()}
    report = {
        "schema_version": "positive-control-audit-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "local_only": True,
        "provider_submission_performed": False,
        "hidden_target_lookup_performed": False,
        "controls": results,
        "interpretation": {
            "p11": "The weighted observed medoid and cluster consensus recover the externally accepted string; most-frequent mode does not.",
            "p12": "Most-frequent, weighted observed medoid, and cluster consensus recover the externally accepted string from the saved 200-shot reconstruction; bitwise majority is 13 bits away.",
            "scope": "This validates the local reconstruction/decoder pipeline on saved data. It does not independently prove the external answer or repair the provider framing defect.",
        },
    }
    (OUT / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    lines = [
        "# P11/P12 positive-control audit",
        "",
        "Local, target-independent reanalysis of saved canonical shot records. No provider submission, HQC spend, or hidden-target lookup was performed.",
        "",
        "## Results",
        "",
        "| Problem | Reconstructed shots | Unique strings | Accepted string recovered by | Max multiplicity | Mean pairwise Hamming |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for name in ("p11", "p12"):
        item = results[name]
        matches = [method for method, ok in item["method_matches_accepted"].items() if ok]
        lines.append(
            f"| {name.upper()} | {item['reconstructed_shots']} | {item['unique_strings']} | {', '.join(matches) or 'none'} | {item['maximum_multiplicity']} | {item['mean_pairwise_hamming']:.6f} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- P11 is a positive control for medoid/cluster recovery: those two methods return the externally accepted 98-bit string, while the simple mode does not.",
        "- P12 is a stronger positive control: most-frequent, weighted observed medoid, and cluster consensus return the externally accepted string; bitwise majority is 13 bits away.",
        "- This is verification of the local analysis and saved-data handling, not a classical simulation of either circuit.",
        "- The audit does not independently re-fetch provider chunks. P11's saved shot file contains 51 records despite a 50-shot request; P12's saved reconstruction contains 200 records after five framing cycles were excluded from a 205-cycle payload.",
        "- P6 must therefore be compared against this corrected positive-control behavior, not against its earlier SDK-assembled apparent repeats.",
        "",
        "## Reproducibility",
        "",
        "The machine-readable report is `audit.json`; all input paths and SHA-256 hashes are recorded there.",
    ]
    (OUT / "audit.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({name: {"shots": value["reconstructed_shots"], "matches": value["method_matches_accepted"]} for name, value in results.items()}, indent=2))


if __name__ == "__main__":
    main()
