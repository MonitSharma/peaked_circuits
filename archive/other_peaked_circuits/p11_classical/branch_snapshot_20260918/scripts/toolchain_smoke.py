#!/usr/bin/env python3
"""Small independent smoke tests for every installed external tool."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator


def main() -> None:
    results: dict[str, dict[str, object]] = {}

    # BQSKit exact target construction and unitary fidelity.
    from bqskit import Circuit
    from bqskit import compile as bq_compile

    target_qc = QuantumCircuit(3)
    target_qc.h(0)
    target_qc.cx(0, 1)
    target_qc.cx(1, 2)
    target = Operator(target_qc).data
    compiled = bq_compile(Circuit.from_unitary(target), max_synthesis_size=3, synthesis_epsilon=1e-10, seed=7)
    compiled_unitary = compiled.get_unitary()
    bq_fidelity = float(abs(np.trace(target.conj().T @ compiled_unitary)) / target.shape[0])
    results["bqskit"] = {"status": "PASS" if bq_fidelity >= 1 - 1e-10 else "FAIL", "fidelity": bq_fidelity, "operations": compiled.num_operations}

    # PyZX exact simplification of two cancelling CNOTs.
    import pyzx as zx

    zx_circuit = zx.Circuit(2)
    zx_circuit.add_gate("CNOT", 0, 1)
    zx_circuit.add_gate("CNOT", 0, 1)
    zx_graph = zx.Circuit.to_graph(zx_circuit)
    before_vertices = zx_graph.num_vertices()
    zx.simplify.full_reduce(zx_graph)
    reduced = zx.extract_circuit(zx_graph)
    results["pyzx"] = {"status": "PASS" if len(reduced.gates) == 0 else "FAIL", "before_vertices": before_vertices, "reduced_gates": len(reduced.gates)}

    # QCEC equivalent and intentionally non-equivalent pairs.
    from mqt import qcec

    equivalent = qcec.verify(target_qc, target_qc.copy())
    changed = target_qc.copy()
    changed.x(2)
    non_equivalent = qcec.verify(target_qc, changed)
    eq_name = str(equivalent.equivalence).lower()
    neq_name = str(non_equivalent.equivalence).lower()
    results["qcec"] = {"status": "PASS" if "equivalent" in eq_name and "not" in neq_name else "FAIL", "equivalent": str(equivalent.equivalence), "non_equivalent": str(non_equivalent.equivalence)}

    # DDSIM Bell/GHZ statevector smoke test.
    from mqt import ddsim

    provider = ddsim.DDSIMProvider()
    backend = provider.get_backend("statevector_simulator")
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    job = backend.run(bell)
    state = np.asarray(job.result().get_statevector())
    results["ddsim"] = {"status": "PASS" if np.isclose(abs(state[0]), 1 / np.sqrt(2)) and np.isclose(abs(state[3]), 1 / np.sqrt(2)) else "FAIL", "state_norm": float(np.linalg.norm(state))}

    # Published-style persistent-permutation MPS smoke test.
    from quimb.tensor.circuit import CircuitPermMPS

    perm_mps = CircuitPermMPS(2, max_bond=4)
    perm_mps.apply_gate("H", qubits=(0,))
    perm_mps.apply_gate("CNOT", qubits=(0, 1))
    mps_state = np.asarray(perm_mps.get_psi().to_dense()).reshape(-1)
    results["circuitpermmps"] = {"status": "PASS" if np.isclose(abs(mps_state[0]), 1 / np.sqrt(2)) and np.isclose(abs(mps_state[3]), 1 / np.sqrt(2)) else "FAIL", "state_norm": float(np.linalg.norm(mps_state))}

    output = Path(sys.argv[1] if len(sys.argv) > 1 else "results/p11_final_campaign/toolchain_smoke.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"timestamp": time.time(), "results": results}, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, sort_keys=True))
    if any(result["status"] != "PASS" for result in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
