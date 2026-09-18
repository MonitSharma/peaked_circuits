#!/usr/bin/env python3
"""Run exact dense validation of qstvec, BASS fixed, and BASS adaptive."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from p12_recovery.sparse_campaign.exact_validation import run_panel


def main() -> None:
    results = run_panel()
    output = ROOT / "results/p11_sparse_campaign/exact_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"status": "PASS", "results": results}, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "circuits": len(results)}, indent=2))


if __name__ == "__main__":
    main()
