#!/usr/bin/env python3
"""Generate candidates from a validated small-patch wire correspondence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def apply(bits, mapping):
    return "".join(bits[i] for i in mapping)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output", type=Path)
    ap.add_argument("--candidate", action="append", required=True)
    args = ap.parse_args()
    # The exact 3-qubit match supplies 22->21, 25->58, 36->6. Complete it as
    # one cycle so the candidate transform remains a true wire permutation.
    cycle = [22, 21, 25, 58, 36, 6]
    mapping = list(range(62))
    for source, target in zip(cycle, cycle[1:] + cycle[:1]):
        mapping[source] = target
    inverse = [mapping.index(i) for i in range(62)]
    rows, seen = [], set()
    for item in args.candidate:
        name, _, bits = item.partition("=")
        if len(bits) != 62 or any(ch not in "01" for ch in bits):
            raise ValueError(f"invalid 62-bit candidate: {item}")
        for label, perm in (("identity", list(range(62))), ("patch_cycle", mapping),
                            ("patch_cycle_inverse", inverse)):
            candidate = apply(bits, perm)
            if candidate in seen:
                continue
            seen.add(candidate)
            rows.append({"source": name, "transform": label, "bitstring": candidate,
                         "patch_left_wires": [22, 25, 36],
                         "patch_right_order": [21, 58, 6], "adjoint_right": True,
                         "fidelity": 0.9977993799338968})
    result = {"schema": "p6-patch-candidate-family-v1", "family_size": len(rows),
              "warning": "structural hypotheses only; not validated answers",
              "candidates": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"family_size": len(rows), "mapping": mapping}, indent=2))


if __name__ == "__main__":
    main()
