#!/usr/bin/env python3
"""Compare frozen P5 candidate families without evaluation feedback."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from p12_recovery.peak.consensus import consensus  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--freeze", action="append", type=Path, required=True)
    args = parser.parse_args()
    runs = []
    for path in args.freeze:
        data = json.loads(path.read_text())
        runs.append({"method_family": "MPO" if "MPO" in path.name else "MPS", "candidate": data["candidate"], "source": str(path), "answer_blind": data.get("answer_blind", False)})
    candidates = [run["candidate"] for run in runs]
    if len({len(candidate) for candidate in candidates}) != 1:
        raise SystemExit("frozen candidates have different widths")
    distances = [{"left": left, "right": right, "hamming": sum(a != b for a, b in zip(runs[left]["candidate"], runs[right]["candidate"], strict=True))} for left in range(len(runs)) for right in range(left + 1, len(runs))]
    result = {"schema": "p12-p5-answer-blind-consensus-v1", "answer_blind": True, "runs": runs, "consensus": consensus(runs), "pairwise_hamming": distances, "evaluation_status": "NOT_RUN"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"candidate": result["consensus"]["candidate"], "status": result["consensus"]["status"], "pairwise_hamming": distances}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
