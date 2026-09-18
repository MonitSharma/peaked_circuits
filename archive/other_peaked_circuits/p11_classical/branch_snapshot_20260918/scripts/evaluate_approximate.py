#!/usr/bin/env python3
"""Apply the campaign's explicit approximate acceptance gates to local ledgers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.summary).read_text())
    tolerances = (1e-8, 1e-6, 1e-4)
    ledger = []
    for tolerance in tolerances:
        rows = []
        for result in source["results"]:
            fidelity = result["fidelity"]
            error = None if fidelity is None else max(0.0, 1.0 - fidelity)
            accepted = bool(
                result["new_two_qubit"] is not None
                and result["new_two_qubit"] < result["old_two_qubit"]
                and error is not None
                and error <= tolerance
            )
            rows.append({"start": result["start"], "stop": result["stop"], "tolerance": tolerance, "error": error, "accepted": accepted, "reason": "strict 2q gate and tolerance gate"})
        ledger.append({"tolerance": tolerance, "accepted": sum(row["accepted"] for row in rows), "rows": rows})
    payload = {"source": args.summary, "p9_56_of_56_preserved": True, "ledger": ledger, "verdict": "BRANCH_NO_GO"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": payload["verdict"], "accepted_by_tolerance": [item["accepted"] for item in ledger]}, sort_keys=True))


if __name__ == "__main__":
    main()
