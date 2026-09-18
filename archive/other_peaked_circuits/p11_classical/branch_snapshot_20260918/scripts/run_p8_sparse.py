#!/usr/bin/env python3
"""Bounded sparse computational-basis simulation for P8.

The P8-specific kernel applies iSWAP as a basis-index permutation plus phase;
therefore only one-qubit rotations can expand the retained support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from p12_recovery.bluequbit.sparse_sv import SparseState, _rss_bytes, dependency_schedule
from p12_recovery.bluequbit.profile import _u_matrix
from structural.qasm_events import parse_qasm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--p-frac", type=float, default=1.0)
    parser.add_argument("--schedule", choices=("original", "cz_first"), default="cz_first")
    parser.add_argument("--max-seconds", type=float, default=1800.0)
    parser.add_argument("--max-rss-bytes", type=int, default=30 * 1024**3)
    args = parser.parse_args()
    if args.top_k <= 0:
        raise SystemExit("--top-k must be positive for a bounded P8 run")

    circuit = parse_qasm(args.qasm)
    state = SparseState(circuit.n_qubits)
    events = dependency_schedule(circuit.events, args.schedule)
    started = time.monotonic()
    trace = []
    discarded = 0.0
    cumulative_retained_mass = 1.0
    minimum_cumulative_retained_mass = 1.0
    max_support = state.support
    iswap_before = iswap_after = 0
    aborted = None
    completed = 0
    for event in events:
        if event.gate == "u":
            state.evolve_u(_u_matrix(*event.params), event.wires[0])
        elif event.gate == "iswap":
            before = state.support
            state.evolve_iswap(*event.wires)
            iswap_before += before
            iswap_after += state.support
            if state.support != before:
                raise RuntimeError("iSWAP changed sparse support before truncation")
        elif event.gate == "cz":
            state.evolve_cz(*event.wires)
        else:
            raise ValueError(f"P8 sparse adapter does not support {event.gate!r}")
        norm_before = state.norm
        trunc = state.truncate(args.top_k, args.p_frac)
        retained_fraction = (
            1.0 - float(trunc["discarded_mass"]) / norm_before
            if norm_before > 0 else 0.0
        )
        cumulative_retained_mass *= max(0.0, min(1.0, retained_fraction))
        minimum_cumulative_retained_mass = min(
            minimum_cumulative_retained_mass, cumulative_retained_mass
        )
        discarded += float(trunc["discarded_mass"])
        max_support = max(max_support, state.support)
        completed += 1
        if event.index % 25 == 0 or trunc["renormalized"]:
            trace.append({"event_index": event.index, "gate": event.gate,
                          "support": state.support,
                          "support_before_truncation": trunc["support_before"],
                          "discarded_mass": trunc["discarded_mass"],
                          "retained_mass_fraction": retained_fraction,
                          "cumulative_retained_mass": cumulative_retained_mass,
                          "norm": state.norm, "rss_bytes": _rss_bytes()})
        if _rss_bytes() >= args.max_rss_bytes:
            aborted = "rss_hard_abort"
            break
        if time.monotonic() - started >= args.max_seconds:
            aborted = "wall_time_abort"
            break

    result = {
        "schema": "p8-sparse-iswap-v1",
        "blind": True,
        "qasm_path": str(args.qasm.resolve()),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "configuration": {"top_k": args.top_k, "p_frac": args.p_frac,
                           "schedule": args.schedule,
                           "max_seconds": args.max_seconds,
                           "max_rss_bytes": args.max_rss_bytes},
        "progress": {"events_completed": completed, "events_total": len(events),
                     "aborted": aborted},
        "runtime_s": time.monotonic() - started,
        "peak_rss_bytes": _rss_bytes(),
        "max_support": max_support,
        "final_support": state.support,
        "cumulative_discarded_mass_proxy": discarded,
        "minimum_cumulative_retained_mass": minimum_cumulative_retained_mass,
        "final_norm": state.norm,
        "iswap_support_preserved": iswap_before == iswap_after,
        "iswap_support_before_total": iswap_before,
        "iswap_support_after_total": iswap_after,
        "top_candidates": state.top(32),
        "trace": trace,
    }
    if len(result["top_candidates"]) >= 2:
        result["top1_probability"] = result["top_candidates"][0]["probability_renormalized"]
        result["top2_probability"] = result["top_candidates"][1]["probability_renormalized"]
        result["top1_top2_ratio"] = (
            result["top1_probability"] / result["top2_probability"]
            if result["top2_probability"] else None
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
