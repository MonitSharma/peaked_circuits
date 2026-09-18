#!/usr/bin/env python3
"""Build blind P1 v2 evidence tables from approximate method outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from p12_recovery.bluequbit.consensus import summarize_consensus


def main() -> None:
    root = Path("results/bluequbit_p1_v2")
    sparse = {}
    for path in sorted((root / "sparse").glob("k*/run.json")):
        data = json.loads(path.read_text())
        if data.get("top_candidates"):
            sparse[path.parent.name] = data["top_candidates"][0]["bitstring"]
    for path in sorted((root / "sparse").glob("blocks_*.json")):
        if "invalid_pre_fix" in path.name:
            continue
        data = json.loads(path.read_text())
        if data.get("top_candidates"):
            sparse[path.stem] = data["top_candidates"][0]["bitstring"]
    for path in sorted((root / "sparse").glob("qstvec_sharp_p1_k*.json")):
        data = json.loads(path.read_text())
        if data.get("top1"):
            sparse[path.stem] = data["top1"]
    mps = {}
    for path in sorted(Path("results/bluequbit_p1/distillation").glob("mettleq_mps_d64_fiedler_lookahead4*/run.json")):
        data = json.loads(path.read_text())
        mps[path.parent.name] = "".join(str(row["predicted_bit"]) for row in data["marginals"])
    distillation = {}
    for path in sorted((root / "distillation").glob("p1_*.json")):
        data = json.loads(path.read_text())
        if data.get("voted_bitstring"):
            distillation[path.stem] = data["voted_bitstring"]
    evidence = {"sparse_top1": sparse.values(), "mps_weak": mps.values(), "distillation_weak": distillation.values()}
    result = summarize_consensus(evidence, 36)
    out = root / "consensus"
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidates.json").write_text(json.dumps({"summary": result, "candidate_sources": {"sparse": sparse, "mps": mps, "distillation": distillation}}, indent=2) + "\n")
    with (out / "bit_evidence.csv").open("w", newline="") as handle:
        fields = ["bit_index_msb_string", "classification", "selected_value", "value_counts", "supporting_methods"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in result["bits"]:
            writer.writerow({key: json.dumps(row[key], sort_keys=True) if isinstance(row[key], (dict, list)) else row[key] for key in fields})


if __name__ == "__main__":
    main()
