#!/usr/bin/env python3
"""Run the bounded answer-blind P8 tree-tensor-network simulator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from p12_recovery.peak.qasm import Gate, parse  # noqa: E402
from p12_recovery.peak.ttn_state import simulate_ttn  # noqa: E402
from p12_recovery.peak.watchdog import tree_rss_bytes  # noqa: E402

CZ = np.diag([1, 1, 1, -1]).astype(np.complex128)
CX = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=np.complex128)


def _u(theta: float, phi: float, lam: float) -> np.ndarray:
    return np.array([[np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
                     [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)]])


def gate_matrix(gate: Gate) -> np.ndarray:
    if gate.name == "u":
        return _u(*gate.params)
    if gate.name == "cz":
        return CZ
    if gate.name == "cx":
        return CX
    if gate.name == "iswap":
        return np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]], dtype=np.complex128)
    if gate.name == "h":
        return np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
    if gate.name == "x":
        return np.array([[0, 1], [1, 0]], dtype=np.complex128)
    if gate.name == "y":
        return np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
    if gate.name == "z":
        return np.diag([1, -1]).astype(np.complex128)
    raise ValueError(f"unsupported gate {gate.name}")


def run(args: argparse.Namespace) -> dict[str, object]:
    source = Path(args.qasm)
    circuit = parse(source)
    state = simulate_ttn(circuit, max_bond=args.max_bond, cutoff=args.cutoff, tree_mode=args.tree_mode)
    started = time.monotonic()
    peak_rss = 0
    for index, gate in enumerate(circuit.gates, 1):
        if time.monotonic() - started >= args.wall_seconds:
            raise TimeoutError("wall_limit")
        if len(gate.qubits) == 1:
            state.apply_one_qubit(gate.qubits[0], gate_matrix(gate))
        elif len(gate.qubits) == 2:
            state.apply_two_qubit(gate.qubits[0], gate.qubits[1], gate_matrix(gate))
        else:
            raise ValueError(f"unsupported gate arity: {gate}")
        peak_rss = max(peak_rss, tree_rss_bytes(os.getpid()))
        if peak_rss > args.rss_limit_gb * (1 << 30):
            raise MemoryError("rss_limit")
        if index % args.progress_every == 0:
            print(f"[{index}/{len(circuit.gates)}] elapsed={time.monotonic() - started:.1f}s rss={peak_rss / 2**30:.2f}GiB", flush=True)
    decoded = state.decode(beam_width=args.beam_width)
    return {
        "schema": "p12-p8-ttn-run-v1",
        "problem": "P8",
        "method_family": "TTN",
        "status": "COMPLETE",
        "answer_blind": True,
        "qasm_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "n_qubits": circuit.n_qubits,
        "gate_count": len(circuit.gates),
        "max_bond": args.max_bond,
        "cutoff": args.cutoff,
        "tree_mode": args.tree_mode,
        "beam_width": args.beam_width,
        "candidate": decoded.bitstring,
        "candidate_probability_in_approximate_ttn": decoded.probability,
        "approximate_total_mass": decoded.total_mass,
        "nodes_expanded": decoded.nodes_expanded,
        "truncation_events": state.truncation_events,
        "discarded_weight_proxy": state.discarded_weight_proxy,
        "runtime_s": time.monotonic() - started,
        "peak_process_tree_rss_bytes": peak_rss,
        "joint_map_claim": "heuristic_beam_over_approximate_ttn",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-bond", type=int, default=4)
    parser.add_argument("--cutoff", type=float, default=1e-10)
    parser.add_argument("--tree-mode", choices=("weighted", "unweighted"), default="weighted")
    parser.add_argument("--beam-width", type=int, default=64)
    parser.add_argument("--wall-seconds", type=float, default=1200.0)
    parser.add_argument("--rss-limit-gb", type=float, default=24.0)
    parser.add_argument("--progress-every", type=int, default=100)
    args = parser.parse_args()
    try:
        result = run(args)
        code = 0
    except Exception as exc:
        result = {"schema": "p12-p8-ttn-run-v1", "problem": "P8", "method_family": "TTN", "status": "ABORTED", "answer_blind": True, "error_type": type(exc).__name__, "error": str(exc)}
        code = 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result.get(key) for key in ("status", "candidate", "runtime_s", "peak_process_tree_rss_bytes", "error_type", "error")}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
