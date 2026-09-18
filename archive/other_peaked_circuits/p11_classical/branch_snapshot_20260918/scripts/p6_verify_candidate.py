#!/usr/bin/env python3
"""Pre-submission filter for P6 candidates.

Every recorded (candidate, overlap) pair is a hard constraint on the truth:

    d(recorded_i, truth) = 62 - overlap_i

So any hypothesis ``x`` must satisfy ``d(recorded_i, x) == 62 - overlap_i`` for
every recorded row.  A violation *proves* ``x`` is not the answer -- this is a
necessary condition, never a sufficient one (C10 and C12 satisfied every
constraint and still scored 30/62).

Use it to reject simulated candidates before spending a submission on them.
It consumes only already-recorded scores; it does not query anything.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / "docs/P6_CANDIDATE_LEDGER.md"
ROW = re.compile(r"^\|\s*(\S+)\s*\|[^|]*\|\s*\**(\d+)/(\d+)\**\s*\|\s*`([01]+)`\s*\|")


def load_constraints(path: Path = LEDGER):
    rows = []
    for line in path.read_text().splitlines():
        m = ROW.match(line.strip())
        if m:
            name, ov, total, bits = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            if len(bits) != total:
                raise SystemExit(f"ledger row {name}: {len(bits)} bits but overlap is out of {total}")
            rows.append({"id": name, "overlap": ov, "n": total, "bits": bits})
    if not rows:
        raise SystemExit(f"no scored rows parsed from {path}")
    return rows


def check(candidate: str, rows):
    n = len(candidate)
    results, ok = [], True
    for r in rows:
        if r["n"] != n:
            raise SystemExit(f"length mismatch: candidate {n} vs ledger {r['n']}")
        agree = sum(a == b for a, b in zip(candidate, r["bits"]))
        consistent = agree == r["overlap"]
        ok &= consistent
        results.append({"id": r["id"], "required_overlap": r["overlap"],
                        "actual_overlap": agree, "delta": agree - r["overlap"],
                        "consistent": consistent})
    return ok, results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", help="62-bit string, or a path to a summary.json")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    cand = args.candidate
    p = Path(cand)
    if p.is_file():
        cand = json.loads(p.read_text())["predicted_bitstring"]
    if set(cand) - {"0", "1"}:
        raise SystemExit("candidate must be a binary string")

    rows = load_constraints()
    ok, results = check(cand, rows)
    print(f"candidate: {cand}")
    print(f"checked against {len(rows)} recorded overlaps\n")
    print(f"  {'id':6s} {'required':>9s} {'actual':>7s} {'delta':>6s}  verdict")
    for r in results:
        print(f"  {r['id']:6s} {r['required_overlap']:>9d} {r['actual_overlap']:>7d} "
              f"{r['delta']:>+6d}  {'ok' if r['consistent'] else 'VIOLATION'}")
    print()
    if ok:
        print("  CONSISTENT with every recorded overlap.")
        print("  This is necessary, NOT sufficient -- C10/C12 were consistent and scored 30/62.")
    else:
        bad = sum(1 for r in results if not r["consistent"])
        print(f"  REJECTED: violates {bad}/{len(rows)} recorded overlaps.")
        print("  This candidate is provably not the answer. Do not submit it.")
    if args.json:
        args.json.write_text(json.dumps({"candidate": cand, "consistent": ok,
                                         "checks": results}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
