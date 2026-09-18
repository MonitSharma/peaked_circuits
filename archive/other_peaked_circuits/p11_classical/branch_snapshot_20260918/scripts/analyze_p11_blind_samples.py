#!/usr/bin/env python3
"""Run the preregistered, zero-compute P11 blind sample analysis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from p12_recovery.p11_extraction import analyze_samples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run5", type=Path, required=True, help="5e-3 samples.tsv")
    parser.add_argument("--run4", type=Path, required=True, help="4e-3 samples.tsv")
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    result = analyze_samples(args.run5, args.run4, args.outdir)
    print(json.dumps({"decision_grade": result["decision_grade"], "outdir": str(args.outdir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
