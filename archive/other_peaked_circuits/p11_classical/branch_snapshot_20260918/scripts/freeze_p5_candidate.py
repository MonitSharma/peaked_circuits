#!/usr/bin/env python3
"""Freeze an answer-blind P5 candidate before any external evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reliability", type=Path, required=True)
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reliability = json.loads(args.reliability.read_text())
    candidate = reliability.get("candidate")
    if not isinstance(candidate, str) or set(candidate) - {"0", "1"}:
        raise SystemExit("reliability artifact does not contain a binary candidate")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    payload = {
        "schema": "p12-p5-candidate-freeze-v1",
        "candidate": candidate,
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "reliability_source": str(args.reliability),
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "git_head": head,
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "answer_blind": True,
        "evaluation_status": "NOT_RUN_AT_FREEZE",
        "rationale": "candidate generated from frozen approximation outputs; no target answer or score oracle was provided",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
