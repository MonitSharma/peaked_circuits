#!/usr/bin/env python3
"""Summarize only aggregate historical unswap telemetry as a soft-prior audit."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

PATTERN = re.compile(
    r"\[(?P<cycle>\d+) \| (?P<side>both|left|right) \| (?P<layer>\d+)\].*?new_swaps: (?P<new>\d+).*?total: (?P<total>\d+)"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    files = []
    for root in args.root:
        for path in root.rglob("*.log"):
            files.append(str(path))
            for line in path.read_text(errors="replace").splitlines():
                match = PATTERN.search(line)
                if match:
                    row = {
                        key: int(value) if key in {"cycle", "layer", "new", "total"} else value
                        for key, value in match.groupdict().items()
                    }
                    row["run"] = path.parent.name
                    row["family"] = "P11" if "p11" in str(path).lower() else "unknown"
                    rows.append(row)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "unswap_aggregate.csv").open("w", newline="") as handle:
        fields = ["run", "family", "cycle", "side", "layer", "new", "total"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "summary.json").write_text(
        json.dumps(
            {
                "schema": "unswap-prior-audit-v1",
                "files_scanned": files,
                "records": len(rows),
                "pair_identity_available": False,
                "decision": "aggregate-only-soft-prior-not-constructed",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
