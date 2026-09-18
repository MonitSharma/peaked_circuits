#!/usr/bin/env python3
"""Generate a small, explicitly tagged family from a structural permutation lead.

This is hypothesis generation only.  No supplied overlap labels are read.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_candidate(item: str) -> tuple[str, str]:
    name, sep, bits = item.partition("=")
    if not sep or not name or any(ch not in "01" for ch in bits):
        raise ValueError(f"invalid candidate: {item}")
    return name, bits


def permute(bits: str, mapping: list[int]) -> str:
    return "".join(bits[index] for index in mapping)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scan", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--candidate", action="append", required=True)
    args = ap.parse_args()
    scan = json.loads(args.scan.read_text())
    mapping = scan["unitary_best"]["permutation"]
    inverse = [mapping.index(index) for index in range(len(mapping))]
    family = []
    seen = set()
    for name, bits in map(parse_candidate, args.candidate):
        if len(bits) != len(mapping):
            raise ValueError(f"{name} has {len(bits)} bits, expected {len(mapping)}")
        transforms = {
            "identity": bits,
            "unitary_perm": permute(bits, mapping),
            "unitary_inverse": permute(bits, inverse),
            "reverse": bits[::-1],
            "complement": bits.translate(str.maketrans("01", "10")),
            "perm_complement": permute(bits.translate(str.maketrans("01", "10")), mapping),
        }
        for transform, candidate in transforms.items():
            key = (candidate, transform)
            if key in seen:
                continue
            seen.add(key)
            family.append({"source": name, "transform": transform,
                           "bitstring": candidate,
                           "structural_lead": {"center_layer": scan["unitary_best"]["center_layer"],
                                                "span": scan["unitary_best"]["span"],
                                                "adjoint_right": scan["unitary_best"]["adjoint_right"],
                                                "score": scan["unitary_best"]["score"]}})
    result = {"schema": "p6-structural-candidate-family-v1",
              "source_scan": str(args.scan), "family_size": len(family),
              "warning": "hypothesis family only; no candidate is validated",
              "candidates": family}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"family_size": len(family), "mapping": mapping}, indent=2))


if __name__ == "__main__":
    main()
