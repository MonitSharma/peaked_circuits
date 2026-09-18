#!/usr/bin/env python3
"""Build a strictly answer-blind P5 reliability artifact from frozen samples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from p12_recovery.peak.ensemble import read_bitstrings, reliability, summarize_samples  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample", action="append", type=Path, required=True)
    parser.add_argument("--column", default="permuted")
    args = parser.parse_args()
    runs = []
    for path in args.sample:
        samples = read_bitstrings(path, column=args.column)
        runs.append(summarize_samples(samples, method_family=path.parts[-3], run_id=path.stem, source=path))
    result = reliability(runs)
    result["runs"] = runs
    result["evaluation_status"] = "NOT_RUN_CANDIDATE_GENERATION_ONLY"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"candidate": result["candidate"], "run_count": result["run_count"], "method_families": result["method_families"], "counts": result["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
