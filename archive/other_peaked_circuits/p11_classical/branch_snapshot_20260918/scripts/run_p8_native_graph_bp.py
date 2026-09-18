#!/usr/bin/env python3
"""Run native P8 graph evolution with Quimb 2-norm BP compression."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from p12_recovery.peak.native_graph import reconstruct_native_graph
from p12_recovery.peak.native_graph_state import NativeGraphState
from p12_recovery.peak.native_graph_decoder import decode_graph_state
from p12_recovery.bluequbit.profile import _u_matrix
from structural.qasm_events import parse_qasm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--max-bond", type=int, required=True)
    parser.add_argument("--cutoff", type=float, default=1e-10)
    parser.add_argument("--max-seconds", type=float, default=1800.0)
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--decode-beam", type=int, action="append", default=[])
    args = parser.parse_args()
    parsed = parse_qasm(args.qasm)
    graph = reconstruct_native_graph(args.qasm)
    state = NativeGraphState(graph, args.max_bond, args.cutoff)
    started = time.monotonic()
    trace = []
    completed = 0
    aborted = None
    for event in parsed.events:
        if args.max_events is not None and completed >= args.max_events:
            aborted = "event_limit"
            break
        if time.monotonic() - started >= args.max_seconds:
            aborted = "wall_time_limit"
            break
        if event.gate == "u":
            state.apply_one(_u_matrix(*event.params), event.wires[0])
            env = {"bp_skipped_local_gate": True}
        elif event.gate == "iswap":
            state.apply_iswap(*event.wires)
            env = state.environment_compress()
        else:
            raise ValueError(f"unsupported native P8 gate {event.gate!r}")
        completed += 1
        trace.append({"event": event.index, "gate": event.gate,
                      "max_bond": state.max_bond_observed(), "norm": state.norm(), **env})
    result = {
        "schema": "p8-native-graph-2norm-bp-v1",
        "qasm": str(args.qasm.resolve()),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": graph.n_qubits,
        "edge_count": len(graph.edges),
        "native_edge_assertion": True,
        "configuration": {"max_bond": args.max_bond, "cutoff": args.cutoff,
                           "max_seconds": args.max_seconds, "max_events": args.max_events},
        "events_completed": completed,
        "events_total": len(parsed.events),
        "aborted": aborted,
        "runtime_s": time.monotonic() - started,
        "final_norm": state.norm(),
        "final_max_bond": state.max_bond_observed(),
        "trace": trace,
    }
    if args.decode_beam:
        result["decoding"] = {
            str(width): decode_graph_state(state, width) for width in args.decode_beam
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("events_completed", "events_total", "aborted", "runtime_s", "final_norm", "final_max_bond")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
