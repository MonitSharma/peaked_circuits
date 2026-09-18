#!/usr/bin/env python3
"""Create the exact SWAP-free permutation-frame form of a P8 QASM circuit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from p12_recovery.peak.iswap_frame import lower_iswap_frame, write_frame_qasm
from p12_recovery.peak.qasm import parse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--out-qasm", type=Path, required=True)
    parser.add_argument("--out-map", type=Path, required=True)
    args = parser.parse_args()

    source = parse(args.qasm)
    frame = lower_iswap_frame(source)
    args.out_qasm.parent.mkdir(parents=True, exist_ok=True)
    args.out_map.parent.mkdir(parents=True, exist_ok=True)
    write_frame_qasm(frame, args.out_qasm)
    record = {
        "schema": "p12-iswap-permutation-frame-v1",
        "answer_blind": True,
        "source_qasm": str(args.qasm),
        "source_qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "frame_qasm": str(args.out_qasm),
        "frame_qasm_sha256": hashlib.sha256(args.out_qasm.read_bytes()).hexdigest(),
        "n_qubits": frame.n_qubits,
        "source_gate_count": frame.source_gate_count,
        "frame_gate_count": len(frame.gates),
        "iswap_count": frame.iswap_count,
        "semantic_permutation": {
            "logical_to_site": list(frame.logical_to_site),
            "site_to_logical": list(frame.site_to_logical),
        },
        "note": "The frame permutation is separate from any MPO routing permutation.",
    }
    args.out_map.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
