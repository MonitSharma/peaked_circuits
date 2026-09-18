#!/usr/bin/env python3
"""Re-run the P11/P12 classical recovery and record measured local runtime.

This is offline-only. It reads packaged canonical shots, validates their
shape, computes the four deterministic recovery methods, and writes a
machine-readable runtime/audit record into the selected tracker package.
It never contacts a provider and never reads credentials.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from p12_recovery.counts_io import validate_canonical_bitstring  # noqa: E402
from p12_recovery.recovery import (  # noqa: E402
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)


CONFIG = {
    "p11": {
        "shot_file": "classical/raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl",
        "accepted": "10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000",
        "job_id": "c902a6a1-0e91-48cf-b5ba-44831fcc7726",
    },
    "p12": {
        "shot_file": "classical/raw/reconstructed_200_shots.jsonl",
        "accepted": "10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100",
        "job_id": "d5cba0df-a7aa-459e-ac51-8092645c059f",
    },
}


def run(package_name: str) -> None:
    package = ROOT / "results" / "tracker_submissions" / package_name
    config = CONFIG[package_name]
    shot_path = package / config["shot_file"]
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    records = [json.loads(line) for line in shot_path.read_text().splitlines() if line.strip()]
    shots = [record["canonical_bitstring"] for record in records]
    for shot in shots:
        validate_canonical_bitstring(shot)
    counts = Counter(shots)
    candidates = [
        most_frequent_string(counts),
        bitwise_majority_string(counts),
        weighted_observed_medoid(counts),
        cluster_consensus(counts),
    ]
    elapsed_wall = time.perf_counter() - started_wall
    elapsed_cpu = time.process_time() - started_cpu
    candidate_map = {candidate.method_name: candidate.canonical_bitstring for candidate in candidates}
    accepted = config["accepted"]
    report = {
        "schema_version": "tracker-classical-runtime-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "problem": package_name,
        "provider_job_id": config["job_id"],
        "input": {
            "path": str(shot_path.relative_to(ROOT)),
            "shots": len(shots),
            "unique_strings": len(counts),
            "bit_length": len(shots[0]),
        },
        "method": {
            "name": "Deterministic frequency, majority, weighted observed medoid, and cluster consensus reanalysis",
            "implementation": "src/p12_recovery/recovery.py",
            "provider_contacted": False,
            "hidden_target_lookup": False,
        },
        "runtime": {
            "wall_seconds": elapsed_wall,
            "cpu_seconds": elapsed_cpu,
            "measurement_scope": "input loading, validation, counts, and four recovery methods",
            "measurement_clock": "time.perf_counter and time.process_time",
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
        },
        "candidates": candidate_map,
        "externally_supplied_accepted_answer": accepted,
        "matches_accepted_answer": {name: value == accepted for name, value in candidate_map.items()},
        "method_agreement": method_agreement(candidates),
        "quantum_advantage_claim": False,
    }
    output = package / "classical" / "runtime_audit.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{package_name}: {elapsed_wall:.9f} wall seconds, {elapsed_cpu:.9f} CPU seconds -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", choices=sorted(CONFIG), nargs="+", help="package(s) to reanalyse")
    args = parser.parse_args()
    for package_name in args.package:
        run(package_name)


if __name__ == "__main__":
    main()

