#!/usr/bin/env python3
"""Bounded Quimb D1BP feasibility probe for P1, with failure capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
import traceback
from pathlib import Path

import numpy as np
import quimb.tensor as qtn

from p12_recovery.bluequbit.profile import _u_matrix
from structural.qasm_events import parse_qasm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--max-iterations", type=int, default=20)
    args = parser.parse_args()
    circuit = parse_qasm(args.qasm)
    started = time.monotonic()
    result = {"schema": "bluequbit-p1-v2-bp-probe-v1", "blind": True, "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(), "algorithm": "quimb.contract_d1bp", "max_iterations": args.max_iterations, "backend": {"python": platform.python_version(), "quimb": __import__('importlib.metadata').metadata.version('quimb')}, "circuit_tensors": None, "status": None}
    try:
        circuit_tn = qtn.Circuit(circuit.n_qubits)
        cz = np.diag([1, 1, 1, -1]).astype(np.complex128)
        for event in circuit.events:
            if event.gate == "u":
                circuit_tn.apply_gate(_u_matrix(*event.params), event.wires[0])
            elif event.gate == "cz":
                circuit_tn.apply_gate(cz, *event.wires)
        psi = circuit_tn.get_psi()
        result["circuit_tensors"] = len(psi.tensor_map)
        result["open_indices"] = len(psi.ind_map)
        from quimb.tensor.belief_propagation import contract_d1bp
        info = {}
        contract_d1bp(psi, max_iterations=args.max_iterations, tol=1e-3, info=info, progbar=False, check_zero=False)
        result.update({"status": "CONVERGED_OR_RETURNED", "info": info})
    except Exception as exc:
        result.update({"status": "REJECTED_FEASIBILITY", "error_type": type(exc).__name__, "error": str(exc).splitlines()[-1], "traceback_tail": traceback.format_exc().splitlines()[-8:]})
    result["runtime_s"] = time.monotonic() - started
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
