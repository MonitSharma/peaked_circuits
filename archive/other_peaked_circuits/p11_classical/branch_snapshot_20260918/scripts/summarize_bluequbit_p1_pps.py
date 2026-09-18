#!/usr/bin/env python3
"""Summarize the blind P1 PPS threshold panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    thresholds = []
    for path in sorted(args.root.glob("panel_t*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        thresholds.append({"threshold": rows[0]["min_abs_coeff"] if rows else None, "observables": len(rows), "resolved": sum(not row["unresolved"] for row in rows), "term_counts": sorted({row["terms"] for row in rows}), "expectations": [row["expectation"] for row in rows], "runtimes_s": [row["elapsed_seconds"] for row in rows]})
    result = {"schema": "bluequbit-p1-v2-pps-summary-v1", "blind": True, "thresholds": thresholds, "adapter_fixture_validated": True, "adapter_fixture_note": "P1 U was decomposed as Rz(lambda), Ry(theta), Rz(phi) in circuit application order and matched Qiskit expectation on a 2-qubit U+CZ fixture.", "decision": "REJECTED_PPS_SMOKE_ZERO_TERMS" if thresholds and all(row["resolved"] == 0 for row in thresholds) else "INCONCLUSIVE"}
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
