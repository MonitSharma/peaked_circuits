#!/usr/bin/env python3
"""Search local Hamming neighborhoods of a bounded CircuitPermMPS state."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn
from qiskit import QuantumCircuit
from qiskit_quimb import quimb_circuit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--max-bond", type=int, required=True)
    ap.add_argument("--cutoff", type=float, default=1e-12)
    ap.add_argument("--starts", type=int, default=16)
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()
    qc = QuantumCircuit.from_qasm_file(str(args.qasm))
    qc.remove_final_measurements()
    started = time.monotonic()
    circuit = quimb_circuit(qc, quimb_circuit_class=qtn.CircuitPermMPS,
                            max_bond=args.max_bond, cutoff=args.cutoff,
                            dtype=np.complex128, progbar=False)
    # CircuitPermMPS.amplitude indexes its underlying physical MPS sites.
    # Convert the public sampler's logical strings into that site order.
    logical_to_site = {logical: site for site, logical in enumerate(circuit.qubits)}
    samples = list(circuit.sample(args.starts, seed=args.seed))
    physical_starts = ["".join(sample[logical] for logical in circuit.qubits) for sample in samples]
    modes = []
    for start in physical_starts:
        current = list(start)
        current_score = abs(circuit.amplitude("".join(current))) ** 2
        changed = True
        sweeps = 0
        while changed and sweeps < 8:
            changed = False
            sweeps += 1
            for site in range(circuit.N):
                trial = current.copy()
                trial[site] = "1" if trial[site] == "0" else "0"
                score = abs(circuit.amplitude("".join(trial))) ** 2
                if score > current_score * (1.0 + 1e-12):
                    current, current_score = trial, score
                    changed = True
        logical = ["0"] * circuit.N
        for site, qubit in enumerate(circuit.qubits):
            logical[qubit] = current[site]
        modes.append({"start_logical": samples[len(modes)], "mode_logical": "".join(logical), "mode_probability_mps": float(current_score), "sweeps": sweeps})
    result = {
        "schema": "bluequbit-p1-v2-mps-coordinate-run-v1",
        "blind": True,
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "configuration": {"max_bond": args.max_bond, "cutoff": args.cutoff, "starts": args.starts, "seed": args.seed, "dtype": "complex128"},
        "runtime_s": time.monotonic() - started,
        "modes": modes,
        "unique_modes": sorted({row["mode_logical"] for row in modes}),
        "decision": "INCONCLUSIVE_UNLESS_MODES_STABLE_ACROSS_BONDS",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
