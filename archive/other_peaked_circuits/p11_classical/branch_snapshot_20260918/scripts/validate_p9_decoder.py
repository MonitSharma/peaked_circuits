#!/usr/bin/env python3
"""Validate the official MPO decoder mapping on the public P9 control only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from p12_recovery.peak.portal_mapping import logical_q0_first_to_portal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.summary.read_text())
    params = data.get("parameters", {})
    expected = params.get("expected_bitstring")
    raw_top = data.get("decoder_topk", [{}])[0].get("bitstring")
    permutation = data.get("measurement_perm")
    if not all(isinstance(x, str) for x in (expected, raw_top)):
        raise SystemExit("P9 summary lacks expected bitstring or decoder top-k")
    if not isinstance(permutation, list) or sorted(permutation) != list(range(len(expected))):
        raise SystemExit("P9 summary has invalid measurement permutation")
    converted = logical_q0_first_to_portal(raw_top, [int(x) for x in permutation])
    result = {
        "schema": "p12-p9-decoder-control-v1",
        "control_only": True,
        "summary": str(args.summary),
        "summary_sha256": hashlib.sha256(args.summary.read_bytes()).hexdigest(),
        "settings": {key: params.get(key) for key in ("max_bond", "cutoff", "unswap_threshold", "sabre_trials", "post_sabre_trials", "seed", "decoder", "decoder_beam_width")},
        "raw_decoder_top1_measurement_order": raw_top,
        "measurement_permutation": permutation,
        "converted_decoder_top1_portal_order": converted,
        "expected_published_p9": expected,
        "decoder_top1_matches_expected": converted == expected,
        "sampling_matches_expected": data.get("matches_expected_bitstring") is True,
        "status": "PASS" if converted == expected and data.get("matches_expected_bitstring") is True else "FAIL",
        "target_answer_used": False,
        "p9_positive_control_exception": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "decoder_top1_matches_expected": result["decoder_top1_matches_expected"], "settings": result["settings"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
