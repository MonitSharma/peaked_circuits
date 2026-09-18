#!/usr/bin/env python3
"""Repair the known P11 duplicate created by fused provider shot framing.

The provider requested 50 shots, but the reconstructed payload produced 51
98-bit records.  This tool verifies that the only duplicate is the first
record repeated at reconstructed index 46, preserves the 51-record source
outside the active raw dataset, and writes a corrected 50-shot dataset.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "results" / "tracker_submissions" / "p11"
SOURCE = PACKAGE / "classical" / "raw_reconstructed_51" / "c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl"
OUTPUT = PACKAGE / "classical" / "raw" / "c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl"
COUNTS = PACKAGE / "classical" / "raw" / "c902a6a1-0e91-48cf-b5ba-44831fcc7726.counts.json"
REPAIR = PACKAGE / "classical" / "raw" / "duplicate_frame_repair.json"


def main() -> None:
    records = [json.loads(line) for line in SOURCE.read_text().splitlines() if line.strip()]
    shots = [record["canonical_bitstring"] for record in records]
    if len(shots) != 51 or any(len(shot) != 98 or set(shot) - {"0", "1"} for shot in shots):
        raise SystemExit("expected exactly 51 valid reconstructed 98-bit records")

    duplicate_groups = {
        shot: [index for index, candidate in enumerate(shots) if candidate == shot]
        for shot, count in Counter(shots).items()
        if count > 1
    }
    expected = {shots[0]: [0, 46]}
    if duplicate_groups != expected:
        raise SystemExit(f"unexpected duplicate structure: {duplicate_groups}")

    corrected = [record for index, record in enumerate(records) if index != 46]
    for index, record in enumerate(corrected):
        record["shot_index"] = index
    OUTPUT.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in corrected))

    counts = Counter(record["canonical_bitstring"] for record in corrected)
    COUNTS.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n")
    REPAIR.write_text(json.dumps({
        "schema_version": "p11-duplicate-frame-repair-v1",
        "provider_requested_shots": 50,
        "raw_reconstructed_records": 51,
        "corrected_independent_records": 50,
        "removed_reconstructed_index": 46,
        "duplicate_of_reconstructed_index": 0,
        "duplicate_bitstring": shots[0],
        "duplicate_count_before_repair": 2,
        "duplicate_count_after_repair": 1,
        "basis": "Exact equality of all 98 canonical bits; the raw provider text contains fused shot framing near the final records.",
        "target_used": False,
        "raw_source": str(SOURCE.relative_to(ROOT)),
        "corrected_output": str(OUTPUT.relative_to(ROOT)),
    }, indent=2) + "\n")
    print(f"wrote {OUTPUT} ({len(corrected)} records)")
    print(f"removed reconstructed index 46, duplicate of index 0")


if __name__ == "__main__":
    main()
