#!/usr/bin/env python3
"""Bounded fixed-output amplitude probe with a non-searching greedy path."""

from __future__ import annotations

import argparse
import time

import quimb.tensor as qtn
from qiskit import QuantumCircuit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm")
    ap.add_argument("bitstring")
    ap.add_argument("--rehearse", action="store_true")
    args = ap.parse_args()
    qc = QuantumCircuit.from_qasm_file(args.qasm)
    qc.remove_final_measurements()
    circuit = qtn.Circuit(qc.num_qubits)
    started = time.monotonic()
    for instruction in qc.data:
        operation = instruction.operation
        qubits = [qc.find_bit(q).index for q in instruction.qubits]
        if operation.name == "u":
            circuit.apply_gate("U3", *map(float, operation.params), qubits[0])
        elif operation.name == "cz":
            circuit.apply_gate("CZ", *qubits)
        else:
            raise ValueError(operation.name)
    print({"built_seconds": time.monotonic() - started}, flush=True)
    started = time.monotonic()
    if args.rehearse:
        rehearsal = circuit.amplitude_rehearse(args.bitstring, optimize="greedy", rehearse=True)
        tree = rehearsal["tree"]
        print({"width": rehearsal["W"], "cost_log10": rehearsal["C"],
               "peak_size": tree.peak_size(), "total_flops": tree.total_flops(),
               "rehearse_seconds": time.monotonic() - started}, flush=True)
    else:
        amplitude = circuit.amplitude(args.bitstring, optimize="greedy")
        print({"amplitude": amplitude, "contract_seconds": time.monotonic() - started}, flush=True)


if __name__ == "__main__":
    main()
