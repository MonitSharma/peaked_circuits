#!/usr/bin/env python3
"""Run one bounded, answer-blind Quimb MPS rung for a peak circuit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn

from p12_recovery.peak.mps import best_first_map, iswap_matrix
from p12_recovery.peak.qasm import Gate, parse
from p12_recovery.peak.watchdog import tree_rss_bytes

CZ = np.diag([1, 1, 1, -1]).astype(np.complex128)
CX = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=np.complex128)


def u_matrix(theta: float, phi: float, lam: float) -> np.ndarray:
    return np.array([[np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
                     [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)]])


def ordering(n: int, gates: tuple[Gate, ...], mode: str) -> list[int]:
    if mode == "identity":
        return list(range(n))
    if mode == "heavy_greedy":
        # Reuse the answer-blind weighted backbone heuristic used by the P6
        # structure probe, so this fallback is not an identity-order retry.
        weights = np.zeros((n, n), dtype=float)
        for gate in gates:
            if len(gate.qubits) == 2:
                a, b = gate.qubits
                weights[a, b] += 1
                weights[b, a] += 1
        neighbors = {q: {} for q in range(n)}
        for a in range(n):
            for b in range(n):
                if weights[a, b]:
                    neighbors[a][b] = int(weights[a, b])
        start = max(neighbors, key=lambda q: (sum(neighbors[q].values()), -q))
        result = [start]
        remaining = set(range(n)) - {start}
        while remaining:
            candidate = max(remaining, key=lambda q: (sum(neighbors[q].get(item, 0) for item in result[-3:]), sum(neighbors[q].values()), -q))
            result.append(candidate)
            remaining.remove(candidate)
        return result
    weights = np.zeros((n, n), dtype=float)
    for gate in gates:
        if len(gate.qubits) == 2:
            a, b = gate.qubits
            weights[a, b] += 1
            weights[b, a] += 1
    laplacian = np.diag(weights.sum(axis=1)) - weights
    values, vectors = np.linalg.eigh(laplacian)
    index = 1 if n > 1 and values[1] > 1e-12 else 0
    return [int(q) for q in np.argsort(vectors[:, index])]


def gate_matrix(gate: Gate) -> np.ndarray:
    if gate.name == "u":
        return u_matrix(*gate.params)
    if gate.name == "cz":
        return CZ
    if gate.name == "cx":
        return CX
    if gate.name == "iswap":
        return iswap_matrix()
    if gate.name == "rzz":
        theta = gate.params[0]
        return np.diag(np.exp(-1j * theta / 2 * np.array([1, -1, -1, 1])))
    if gate.name == "h":
        return np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    if gate.name == "x":
        return np.array([[0, 1], [1, 0]])
    if gate.name == "y":
        return np.array([[0, -1j], [1j, 0]])
    if gate.name == "z":
        return np.diag([1, -1])
    raise ValueError(f"unsupported gate {gate.name}")


def _mps_arrays(mps) -> list[np.ndarray]:
    mps = mps.copy()
    mps.right_canonicalize()
    # Decode the normalized approximate state, while the caller separately
    # records the pre-normalization retained_norm_proxy.
    mps.normalize()
    mps.permute_arrays("lpr")
    arrays = []
    for i in range(mps.L):
        array = np.asarray(mps[i].data)
        if array.ndim == 2:
            array = array.reshape(1, *array.shape) if i == 0 else array.reshape(*array.shape, 1)
        arrays.append(array)
    return arrays


def run(args: argparse.Namespace) -> dict:
    source = Path(args.qasm)
    circuit = parse(source)
    order = ordering(circuit.n_qubits, circuit.gates, args.order)
    position = {q: i for i, q in enumerate(order)}
    common = {"max_bond": args.bond, "cutoff": args.cutoff, "dtype": args.dtype,
              "gate_opts": {"cutoff_mode": "rsum2", "renorm": False}}
    sim = qtn.CircuitPermMPS(circuit.n_qubits, **common) if args.engine == "perm" else qtn.CircuitMPS(circuit.n_qubits, **common)
    gates = circuit.gates[:args.max_gates] if args.max_gates else circuit.gates
    started = time.monotonic()
    peak_rss = 0
    checkpoint_count = 0
    checkpoint = Path(args.checkpoint) if args.checkpoint else None
    qasm_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    resume_from = 0
    if checkpoint and checkpoint.exists():
        try:
            saved = json.loads(checkpoint.read_text())
        except (OSError, json.JSONDecodeError):
            saved = {}
        compatible = (
            saved.get("status") == "IN_PROGRESS"
            and saved.get("qasm_sha256") == qasm_sha256
            and saved.get("bond") == args.bond
            and saved.get("cutoff") == args.cutoff
            and saved.get("engine") == args.engine
            and saved.get("order") == args.order
            and saved.get("dtype") == args.dtype
            and saved.get("total_gates") == len(gates)
        )
        if compatible:
            resume_from = min(int(saved.get("gates_completed", 0)), len(gates))
    # Replaying the committed prefix reconstructs the numerical state without
    # serializing backend-specific tensor objects. This makes checkpoints
    # portable across interruption/reboot while remaining deterministic.
    for gate in gates[:resume_from]:
        sites = [position[q] for q in gate.qubits]
        sim.apply_gate_raw(gate_matrix(gate), sites)
    for index, gate in enumerate(gates[resume_from:], resume_from + 1):
        if time.monotonic() - started >= args.wall_seconds:
            raise TimeoutError("wall_limit")
        sites = [position[q] for q in gate.qubits]
        sim.apply_gate_raw(gate_matrix(gate), sites)
        peak_rss = max(peak_rss, tree_rss_bytes(os.getpid()))
        if checkpoint and (index == len(gates) or index % args.checkpoint_every == 0):
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text(json.dumps({"status": "IN_PROGRESS", "qasm_sha256": qasm_sha256, "bond": args.bond, "cutoff": args.cutoff, "engine": args.engine, "order": args.order, "dtype": args.dtype, "gates_completed": index, "total_gates": len(gates), "elapsed_s": time.monotonic() - started, "peak_process_tree_rss_bytes": peak_rss}) + "\n")
            checkpoint_count += 1
    state = sim.get_psi_unordered() if args.engine == "perm" else sim.psi
    retained = float(abs(state.norm()) ** 2)
    result = {"schema": "p12-peak-mps-run-v1", "answer_blind": True, "qasm_sha256": qasm_sha256, "n_qubits": circuit.n_qubits, "gates": len(gates), "full_gate_count": len(circuit.gates), "prefix_run": bool(args.max_gates), "bond": args.bond, "cutoff": args.cutoff, "dtype": args.dtype, "engine": args.engine, "order": order, "retained_norm_proxy": retained, "max_bond_reached": int(state.max_bond() or 1), "runtime_s": time.monotonic() - started, "peak_process_tree_rss_bytes": peak_rss, "checkpoint_count": checkpoint_count, "resumed_from_gates": resume_from}
    arrays = _mps_arrays(state)
    decoded = best_first_map(arrays, max_nodes=args.max_decode_nodes, max_seconds=args.decode_seconds)
    site_index = list(sim.qubits) if args.engine == "perm" else list(range(circuit.n_qubits))
    if decoded.bitstring is not None:
        logical = ["0"] * circuit.n_qubits
        for site, bit in enumerate(decoded.bitstring):
            logical[order[site_index[site]]] = bit
        result["map"] = {"logical_q0_first": "".join(logical), "approximate_probability": decoded.probability, "certified": decoded.certified, "nodes_expanded": decoded.nodes_expanded, "max_queue_size": decoded.max_queue_size, "final_upper_bound": decoded.final_upper_bound, "runner_up": decoded.runner_up}
    result["status"] = "COMPLETE"
    if checkpoint:
        checkpoint.write_text(json.dumps({"status": "COMPLETE", "result": result}, indent=2) + "\n")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qasm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bond", type=int, required=True)
    ap.add_argument("--cutoff", type=float, default=1e-14)
    ap.add_argument("--engine", choices=("perm", "mps"), default="perm")
    ap.add_argument("--order", choices=("identity", "spectral", "heavy_greedy"), default="identity")
    ap.add_argument("--dtype", default="complex128")
    ap.add_argument("--wall-seconds", type=float, default=3600)
    ap.add_argument("--max-gates", type=int, default=0, help="bounded prefix smoke test; zero means the full circuit")
    ap.add_argument("--checkpoint")
    ap.add_argument("--checkpoint-every", type=int, default=250)
    ap.add_argument("--max-decode-nodes", type=int, default=200000)
    ap.add_argument("--decode-seconds", type=float, default=120)
    args = ap.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        result = {"schema": "p12-peak-mps-run-v1", "answer_blind": True, "status": "ABORTED", "reason": f"{type(exc).__name__}: {exc}"}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
        return 2
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
