#!/usr/bin/env python3
"""Verify completed P9 result bundles against the published oracle contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ORACLE = "01101110111001100000100000001010011100101101010111110111"
EXPECTED_QASM_SHA256 = "cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = run_dir / "manifest.json"
    summary_path = run_dir / "summary.json"
    stats_path = run_dir / "stats.json"
    samples_path = run_dir / "samples.tsv"
    if not all(path.exists() for path in (manifest_path, summary_path, stats_path, samples_path)):
        return ["missing required result bundle file"]
    manifest = json.loads(manifest_path.read_text())
    summary = json.loads(summary_path.read_text())
    stats = json.loads(stats_path.read_text())
    if manifest.get("status", "completed") != "completed" or manifest.get("returncode") != 0:
        return ["run is not a completed zero-returncode run"]
    if manifest.get("qasm_sha256") != EXPECTED_QASM_SHA256:
        errors.append("QASM hash mismatch")
    if manifest.get("expected_bitstring") != ORACLE:
        errors.append("manifest oracle mismatch")
    if summary.get("expected_bitstring") != ORACLE:
        errors.append("summary oracle mismatch")
    if summary.get("matches_expected_bitstring") is not True:
        errors.append("modal bitstring does not match oracle")
    diagnostics = summary.get("diagnostics", {})
    if diagnostics.get("work_gates_consumed") != diagnostics.get("total_work_gates"):
        errors.append("work-gate count is incomplete")
    if diagnostics.get("total_work_gates") != 1885:
        errors.append("unexpected total work-gate count")
    if diagnostics.get("measurement_permutation") is not None:
        permutation = diagnostics["measurement_permutation"]
    else:
        permutation = summary.get("measurement_permutation", [])
    if len(permutation) != 56 or sorted(permutation) != list(range(56)):
        errors.append("measurement permutation is not a 56-qubit permutation")
    sample_lines = samples_path.read_text().splitlines()
    if len(sample_lines) != int(summary.get("shots", 0)) + 1:
        errors.append("sample count does not match shots")
    if not stats or not any(row.get("stage") == "termination" for row in stats):
        errors.append("stats lack a termination record")
    required_options = ("max_bond", "cutoff", "seed")
    if any(name not in diagnostics.get("options", {}) for name in required_options):
        errors.append("diagnostics lack required hyperparameters")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_root", type=Path)
    args = parser.parse_args()
    checked = 0
    failures = 0
    for manifest_path in sorted(args.results_root.glob("*/manifest.json")):
        run_dir = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("status", "completed") != "completed" or manifest.get("returncode") != 0:
            continue
        checked += 1
        errors = verify(run_dir)
        if errors:
            failures += 1
            print(f"FAIL {run_dir.name}: {'; '.join(errors)}")
        else:
            print(f"PASS {run_dir.name}")
    print(f"checked={checked} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
