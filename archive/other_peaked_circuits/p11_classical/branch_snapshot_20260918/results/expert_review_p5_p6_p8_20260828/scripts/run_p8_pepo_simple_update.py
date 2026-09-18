#!/usr/bin/env python3
"""Run native-graph PEPO Heisenberg simple-update marginals for P8."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn
from qiskit import QuantumCircuit


ISWAP = np.array(
    [
        [1, 0, 0, 0],
        [0, 0, 1j, 0],
        [0, 1j, 0, 0],
        [0, 0, 0, 1],
    ],
    dtype=np.complex128,
)


def stable_local_expectation(circuit, operator, site, *, max_bond, cutoff):
    """Evaluate one PEPO expectation with bounded, normalized gauges."""
    where = (site,)
    op = circuit._initial_operator(operator, where)
    gauges = {}
    support = {site}
    opts = {
        **circuit.gate_opts,
        "max_bond": max_bond,
        "cutoff": cutoff,
        "renorm": True,
        "smudge": 1e-8,
    }
    for gate in reversed(circuit._gates):
        gate_where = gate.qubits
        if support.isdisjoint(gate_where):
            continue
        support.update(gate_where)
        arr = np.asarray(gate.array)
        dim = int(round(arr.size ** 0.5))
        op.gate_simple_(arr.reshape(dim, dim).conj().T, gate_where, gauges, **opts)
        # Keep every tracked singular-value vector at unit norm. The
        # expectation is contracted as a normalized quantity, while this
        # prevents long reverse lightcones from overflowing.
        for key, value in list(gauges.items()):
            norm = np.linalg.norm(value)
            if np.isfinite(norm) and norm > 0:
                gauges[key] = value / norm
    op.gauge_simple_insert(gauges, smudge=1e-8)
    selectors = {}
    for s in circuit._sites:
        selectors[op.upper_ind(s)] = 0
        selectors[op.lower_ind(s)] = 0
    return op.isel(selectors).contract(all, optimize="greedy")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("--max-bond", type=int, default=16)
    ap.add_argument("--cutoff", type=float, default=1e-3)
    ap.add_argument("--sites", help="Comma-separated logical sites to evaluate (default: all)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    qc = QuantumCircuit.from_qasm_file(str(args.qasm))
    qc.remove_final_measurements()
    edges = sorted({tuple(sorted(qc.find_bit(q).index for q in inst.qubits))
                    for inst in qc.data if len(inst.qubits) == 2})
    started = time.monotonic()
    circuit = qtn.CircuitPEPOSimpleUpdate(
        N=qc.num_qubits,
        edges=edges,
        max_bond=args.max_bond,
        cutoff=args.cutoff,
        dtype="complex128",
        # The default Heisenberg PEPO path preserves operator norm, but on
        # this long circuit its intermediate gauges overflow. Normalization
        # is used only as a numerical exploratory stabilization here.
        gate_opts={"renorm": True},
    )
    for instruction in qc.data:
        operation = instruction.operation
        qubits = [qc.find_bit(q).index for q in instruction.qubits]
        if operation.name in {"u", "u3"}:
            circuit.apply_gate("U3", *map(float, operation.params), qubits[0])
        elif operation.name == "iswap":
            circuit.apply_gate(ISWAP, *qubits)
        else:
            raise ValueError(f"Unsupported operation: {operation.name}")

    projector = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.complex128)
    sites = list(range(qc.num_qubits)) if args.sites is None else [int(x) for x in args.sites.split(",")]
    if any(site < 0 or site >= qc.num_qubits for site in sites):
        raise ValueError("--sites contains an out-of-range site")
    p0 = []
    for site in sites:
        value = stable_local_expectation(
            circuit, projector, site, max_bond=args.max_bond, cutoff=args.cutoff
        )
        p0.append(float(np.real(value)))
    bitstring = "".join("1" if value < 0.5 else "0" for value in p0)
    result = {
        "schema": "bluequbit-p8-pepo-simple-update-v1",
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": qc.num_qubits,
        "gate_count": qc.size(),
        "unique_edges": len(edges),
        "max_bond": args.max_bond,
        "cutoff": args.cutoff,
        "sites": sites,
        "dtype": "complex128",
        "iswap_definition": "explicit_matrix_q0q1=[1, iSWAP, iSWAP, 1]",
        "p0": p0,
        "bitstring_q0_first": bitstring,
        "reversed": bitstring[::-1],
        "weakest_margin": min(abs(x - 0.5) for x in p0),
        "elapsed_s": time.monotonic() - started,
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
