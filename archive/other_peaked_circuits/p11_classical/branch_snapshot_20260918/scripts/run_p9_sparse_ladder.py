#!/usr/bin/env python3
# ruff: noqa: E402
"""Run the explicitly bounded P9-only top-K sparse-state side experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from structural.qasm_events import parse_qasm
from structural.sparse_state import TopKSparseState

TRUE_P9 = "01101110111001100000100000001010011100101101010111110111"


def rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def run(args: argparse.Namespace) -> dict:
    if args.qasm.resolve() != (ROOT / "data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm").resolve():
        raise ValueError("this side experiment is restricted to the canonical P9 input")
    circuit = parse_qasm(args.qasm)
    target_index = int(TRUE_P9[::-1], 2)
    rows = []
    for retained in args.retained:
        state = TopKSparseState(circuit.n_qubits, retained)
        run_started = time.perf_counter()
        result = state.run(circuit, max_seconds=args.max_seconds)
        rows.append(
            {
                "retained_states": retained,
                "steps": result.steps,
                "complete": not result.timed_out and result.steps == len(circuit.events),
                "timed_out": result.timed_out,
                "target_probability": state.probability(target_index),
                "retained_probability": result.retained_probability,
                "cumulative_discarded_probability": result.discarded_probability,
                "runtime_s": result.elapsed_s,
                "peak_rss_bytes": rss_bytes(),
                "wall_s": time.perf_counter() - run_started,
            }
        )
        if result.timed_out:
            break
    output = {
        "schema": "p9-sparse-ladder-v1",
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": circuit.n_qubits,
        "n_events": len(circuit.events),
        "target_is_p9_supervised_calibration": True,
        "target_bitstring_sha256": hashlib.sha256(TRUE_P9.encode()).hexdigest(),
        "retained_ladder": args.retained,
        "max_seconds_per_run": args.max_seconds,
        "rows": rows,
        "decision": "proposal_only" if any(row["complete"] and row["target_probability"] > args.signal_threshold for row in rows) else "stop_no_signal_or_incomplete",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retained", type=int, nargs="+", default=[2**12, 2**14, 2**16, 2**18, 2**20])
    parser.add_argument("--max-seconds", type=float, default=90.0)
    parser.add_argument("--signal-threshold", type=float, default=1e-4)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2))


if __name__ == "__main__":
    main()
