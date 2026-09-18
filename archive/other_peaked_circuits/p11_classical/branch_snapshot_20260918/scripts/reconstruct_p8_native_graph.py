#!/usr/bin/env python3
"""Reconstruct and validate the original P8 native interaction graph."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from p12_recovery.peak.native_graph import reconstruct_native_graph


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    graph = reconstruct_native_graph(args.qasm)
    result = {
        "schema": "p8-native-interaction-graph-v1",
        "qasm": str(args.qasm.resolve()),
        **graph.as_dict(),
        "native_iswap_edge_assertion": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
