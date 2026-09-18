#!/usr/bin/env python3
"""Summarize blind sparse top-k convergence without an oracle."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def jaccard(a: list[str], b: list[str]) -> float:
    left, right = set(a), set(b)
    return len(left & right) / len(left | right) if left | right else 1.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    rows, adjacent = [], []
    paths = [path for path in args.root.glob("k*/run.json") if re.fullmatch(r"k\d+", path.parent.name)]
    for path in sorted(paths, key=lambda p: int(p.parent.name[1:])):
        data = json.loads(path.read_text())
        candidates = data.get("top_candidates", [])
        rows.append({"top_k": data["configuration"]["top_k"], "status": "COMPLETE" if not data["progress"]["aborted"] and data["progress"]["events_completed"] == data["progress"]["events_total"] else "ABORTED", "top1": candidates[0]["bitstring"] if candidates else None, "top1_probability_renormalized": candidates[0]["probability_renormalized"] if candidates else None, "max_support": data.get("max_support"), "discarded_mass_proxy": data.get("cumulative_discarded_mass_proxy"), "runtime_s": data.get("runtime_s"), "peak_rss_bytes": data.get("peak_rss_bytes")})
        if len(rows) >= 2 and candidates:
            previous = json.loads(sorted(paths, key=lambda p: int(p.parent.name[1:]))[len(rows) - 2].read_text()).get("top_candidates", [])
            adjacent.append({"lower_top_k": rows[-2]["top_k"], "higher_top_k": rows[-1]["top_k"], "top1_same": bool(previous and previous[0]["bitstring"] == candidates[0]["bitstring"]), "top5_jaccard": jaccard([x["bitstring"] for x in previous[:5]], [x["bitstring"] for x in candidates[:5]])})
    block_rows = []
    for path in sorted(args.root.glob("blocks_*.json")):
        data = json.loads(path.read_text())
        if "invalid_pre_fix" in path.name:
            continue
        candidates = data.get("top_candidates", [])
        block_rows.append({"run": path.stem, "top_k": data["configuration"]["top_k"], "max_qubits_per_block": data["configuration"]["max_qubits_per_block"], "priority": data["configuration"].get("priority", "cz_first"), "status": "COMPLETE" if data["progress"]["aborted"] is None else "ABORTED", "top1": candidates[0]["bitstring"] if candidates else None, "discarded_mass_proxy": data.get("cumulative_discarded_mass_proxy"), "runtime_s": data.get("runtime_s"), "final_norm": data.get("final_norm")})
    qstvec_rows = []
    for path in sorted(args.root.glob("qstvec_sharp_p1_k*.json"), key=lambda p: int(re.search(r"k(\d+)", p.stem).group(1))):
        data = json.loads(path.read_text())
        qstvec_rows.append({"run": path.stem, "top_k": data["configuration"]["top_k"], "status": "COMPLETE" if data["progress"]["aborted"] is None else "ABORTED", "top1": data.get("top1"), "top1_probability_renormalized": data.get("top1_probability_renormalized"), "runtime_s": data.get("runtime_s"), "final_support": data.get("final_support"), "block_count": data.get("block_count")})
    qstvec_top1_converged = len(qstvec_rows) >= 2 and qstvec_rows[-1]["top1"] == qstvec_rows[-2]["top1"]
    result = {"schema": "bluequbit-p1-v2-sparse-convergence-v1", "blind": True, "runs": rows, "adjacent_comparisons": adjacent, "block_runs": block_rows, "qstvec_sharp_runs": qstvec_rows, "qstvec_sharp_top1_converged": qstvec_top1_converged, "decision": "PROMOTED" if len(rows) >= 2 and all(row["top1"] == rows[-1]["top1"] for row in rows[-2:] if row["top1"]) else "REJECTED_UNCONVERGED_OR_INCONCLUSIVE"}
    (args.root / "convergence.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
