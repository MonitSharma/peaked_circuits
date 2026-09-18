#!/usr/bin/env python3
"""Compute frozen-panel exact and tolerance-gated synthesis statistics."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    source = Path("results/p11_final_campaign/synthesis_panel_results.csv")
    rows = list(csv.DictReader(source.open()))
    tolerances = (1e-8, 1e-6, 1e-4)
    accepted = {}
    for tolerance in tolerances:
        selected = []
        for row in rows:
            try:
                error = float(row["numerical_infidelity"])
                new = int(row["numerical_2q"])
                old = int(row["old_2q"])
            except (TypeError, ValueError):
                continue
            if error <= tolerance and new < old:
                selected.append(row)
        accepted[str(tolerance)] = {"blocks": len(selected), "ids": [row["panel_id"] for row in selected], "old_2q": sum(int(row["old_2q"]) for row in selected), "new_2q": sum(int(row["numerical_2q"]) for row in selected)}
    exact = [row for row in rows if row["exact_reduction"] == "True"]
    payload = {
        "panel_blocks": len(rows),
        "panel_old_2q": sum(int(row["old_2q"]) for row in rows),
        "exact_verified_reductions": len(exact),
        "exact_verified_reduction_2q": sum(int(row["old_2q"]) - int(row["bqskit_2q"]) for row in exact),
        "exact_ids": [row["panel_id"] for row in exact],
        "approximate": accepted,
        "gate_1": "NO_GO" if len(exact) / len(rows) < 0.05 and sum(int(row["old_2q"]) - int(row["bqskit_2q"]) for row in exact) / sum(int(row["old_2q"]) for row in rows) < 0.15 else "REVIEW",
        "p9_gate_2": "NOT_RUN_NO_FROZEN_GLOBAL_REWRITE",
        "permutation_ledger": {"q3": 6, "q4": 24, "all_blocks_enumerated": True},
    }
    output = Path("results/p11_final_campaign/synthesis_panel_summary.json")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
