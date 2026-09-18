#!/usr/bin/env python3
"""Freeze MPO candidates before any external evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    # At solver HEAD b1bed0a, decoder fields are already permuted into the
    # canonical output order. The sampled mode is the authoritative candidate
    # because it shares the exact path validated by the P9 positive control.
    candidate = summary.get("predicted_bitstring")
    topk = summary.get("top_permuted_samples", [])
    if not isinstance(candidate, str) or set(candidate) - {"0", "1"}:
        raise SystemExit("MPO summary has no binary predicted_bitstring")
    canonical_topk = []
    for row in topk:
        if isinstance(row, (list, tuple)) and len(row) == 2:
            bitstring, count = row
            row = {"bitstring": bitstring, "count": count}
        bitstring = row.get("bitstring")
        if not isinstance(bitstring, str) or len(bitstring) != len(candidate):
            raise SystemExit("MPO summary has malformed top_permuted_samples")
        canonical_topk.append(row)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    payload = {
        "schema": "p12-p5-mpo-candidate-freeze-v1",
        "problem": "P5",
        "candidate": candidate,
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "top_k": canonical_topk,
        "decoder_bitwise_map_diagnostic": summary.get("decoder_bitwise_map"),
        "measurement_permutation_recorded_in_summary": summary.get("measurement_perm"),
        "summary": str(args.summary),
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "git_head": head,
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "answer_blind": True,
        "evaluation_status": "NOT_RUN_AT_FREEZE",
        "mapping_source": "MPO predicted_bitstring/top_permuted_samples already canonicalized by solver HEAD; P9 decoder and sampling control validated",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"candidate": candidate, "top_k_count": len(canonical_topk), "evaluation_status": payload["evaluation_status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
