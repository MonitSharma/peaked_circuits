#!/usr/bin/env python3
"""Run the public CircuitPermMPS bitstring-distillation idea on blind P1."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import platform
import resource
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
import quimb.tensor as qtn
from qiskit_quimb import quimb_circuit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--max-bond", type=int, required=True)
    ap.add_argument("--cutoff", type=float, default=1e-12)
    ap.add_argument("--samples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--dtype", choices=("complex64", "complex128"), default="complex128")
    args = ap.parse_args()
    if platform.system() != "Darwin":
        raise SystemExit("P1 distillation runner is Mac-only")
    qc = QuantumCircuit.from_qasm_file(str(args.qasm))
    qc.remove_final_measurements()
    dtype = np.dtype(args.dtype)
    started = time.monotonic()
    circuit = quimb_circuit(
        qc,
        quimb_circuit_class=qtn.CircuitPermMPS,
        max_bond=args.max_bond,
        cutoff=args.cutoff,
        dtype=dtype,
        progbar=False,
    )
    # Match the public notebook's convention: CircuitPermMPS exposes a
    # logical-to-current mapping, and its sampled strings require the second
    # application shown in the reference workflow.
    qubit_mapping = [circuit.qubits.index(q) for q in range(circuit.N)]
    qubit_mapping = [qubit_mapping[q] for q in qubit_mapping]
    samples = ["".join(sample[q] for q in qubit_mapping) for sample in circuit.sample(args.samples, seed=args.seed)]
    counts = collections.Counter(samples)
    bit_probs = np.asarray([[int(bit) for bit in sample] for sample in samples], dtype=float).mean(axis=0)
    voted = "".join(str(int(value > 0.5)) for value in bit_probs)
    result = {
        "schema": "bluequbit-p1-v2-distillation-run-v1",
        "blind": True,
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "configuration": {"max_bond": args.max_bond, "cutoff": args.cutoff, "samples": args.samples, "seed": args.seed, "dtype": args.dtype, "method": "public_CircuitPermMPS_bitstring_distillation"},
        "n_qubits": qc.num_qubits,
        "gate_count": qc.size(),
        "voted_bitstring": voted,
        "voted_bitstring_frequency": int(counts[voted]),
        "bit_probabilities": bit_probs.tolist(),
        "most_common_samples": [{"bitstring": bit, "count": count} for bit, count in counts.most_common(10)],
        "final_qubit_mapping": circuit.qubits,
        "runtime_s": time.monotonic() - started,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "decision": "WEAK_DISTILLATION_SIGNAL_UNLESS_REPEATED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
