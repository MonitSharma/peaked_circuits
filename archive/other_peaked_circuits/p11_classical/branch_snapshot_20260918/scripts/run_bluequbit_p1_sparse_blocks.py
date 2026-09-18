#!/usr/bin/env python3
"""Run qstvec-style dependency-aware small-block sparse simulation on P1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
try:
    import resource
except ImportError:  # pragma: no cover - Windows has no stdlib resource module.
    resource = None
import time
from pathlib import Path

import numpy as np

from p12_recovery.bluequbit.profile import _u_matrix
from p12_recovery.bluequbit.sparse_sv import SparseState
from structural.qasm_events import Event, parse_qasm


def blocks_from_events(events: tuple[Event, ...], max_qubits: int, priority: str = "cz_first") -> list[list[Event]]:
    predecessors: dict[int, int] = {}
    successors = {event.index: [] for event in events}
    indegree = {event.index: 0 for event in events}
    for event in events:
        deps = {predecessors[q] for q in event.wires if q in predecessors}
        indegree[event.index] = len(deps)
        for dep in deps:
            successors[dep].append(event.index)
        for q in event.wires:
            predecessors[q] = event.index
    by_index = {event.index: event for event in events}
    ready = [event.index for event in events if indegree[event.index] == 0]
    blocks: list[list[Event]] = []
    all_qubits: set[int] = set()
    while ready:
        ready.sort(key=lambda i: (len(all_qubits | set(by_index[i].wires)) - len(all_qubits), by_index[i].gate != "cz" if priority == "cz_first" else by_index[i].gate == "cz", i))
        block: list[Event] = []
        block_qubits: set[int] = set()
        while ready:
            ready.sort(key=lambda i: (len(all_qubits | set(by_index[i].wires)) - len(all_qubits), len(block_qubits | set(by_index[i].wires)) - len(block_qubits), by_index[i].gate != "cz" if priority == "cz_first" else by_index[i].gate == "cz", i))
            candidate = by_index[ready[0]]
            candidate_qubits = set(candidate.wires)
            if block and len(block_qubits | candidate_qubits) > max_qubits:
                break
            ready.pop(0)
            block.append(candidate)
            block_qubits |= candidate_qubits
            for successor in successors[candidate.index]:
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    ready.append(successor)
        blocks.append(block)
        all_qubits |= block_qubits
    return blocks


def embed_gate(gate: np.ndarray, gate_qargs: tuple[int, ...], local_qargs: list[int]) -> np.ndarray:
    width = len(local_qargs)
    result = np.zeros((1 << width, 1 << width), dtype=np.complex128)
    positions = [local_qargs.index(q) for q in gate_qargs]
    for column in range(1 << width):
        gate_column = sum(((column >> position) & 1) << i for i, position in enumerate(positions))
        for gate_row in range(1 << len(gate_qargs)):
            row = column
            for position in positions:
                row &= ~(1 << position)
            for i, position in enumerate(positions):
                row |= ((gate_row >> i) & 1) << position
            result[row, column] += gate[gate_row, gate_column]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--max-qubits", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--priority", choices=("cz_first", "u_first"), default="cz_first")
    parser.add_argument("--p-frac", type=float, default=1.0)
    args = parser.parse_args()
    circuit = parse_qasm(args.qasm)
    blocks = blocks_from_events(circuit.events, args.max_qubits, args.priority)
    state = SparseState(circuit.n_qubits)
    started = time.monotonic()
    discarded = 0.0
    trace = []
    aborted = None
    for block_index, block in enumerate(blocks):
        local_qargs = sorted({q for event in block for q in event.wires})
        unitary = np.eye(1 << len(local_qargs), dtype=np.complex128)
        for event in block:
            gate = _u_matrix(*event.params) if event.gate == "u" else np.diag([1, 1, 1, -1]).astype(np.complex128)
            unitary = embed_gate(gate, event.wires, local_qargs) @ unitary
        state.evolve_local(unitary.astype(np.complex128), local_qargs)
        trunc = state.truncate(args.top_k, args.p_frac)
        discarded += float(trunc["discarded_mass"])
        trace.append({"block": block_index, "events": len(block), "event_index_last": block[-1].index, "local_qubits": local_qargs, "support": state.support, "support_before_truncation": trunc["support_before"], "discarded_mass_before_renormalization": trunc["discarded_mass"]})
        if time.monotonic() - started >= args.max_seconds:
            aborted = "wall_time_abort"
            break
    result = {"schema": "bluequbit-p1-v2-sparse-block-run-v1", "blind": True, "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(), "configuration": {"top_k": args.top_k, "p_frac": args.p_frac, "max_qubits_per_block": args.max_qubits, "max_seconds": args.max_seconds, "schedule": "qstvec_style_dependency_ready", "priority": args.priority}, "block_count": len(blocks), "progress": {"blocks_completed": len(trace), "blocks_total": len(blocks), "events_completed": trace[-1]["event_index_last"] + 1 if trace else 0, "events_total": len(circuit.events), "aborted": aborted}, "runtime_s": time.monotonic() - started, "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss), "max_support": max((row["support"] for row in trace), default=state.support), "final_support": state.support, "cumulative_discarded_mass_proxy": discarded, "final_norm": state.norm, "top_candidates": state.top(32), "trace": trace}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
