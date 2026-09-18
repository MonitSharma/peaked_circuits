#!/usr/bin/env python3
"""Run one bounded exact PyZX pipeline on the P9 calibration circuit."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps


def main() -> None:
    import pyzx as zx

    source = Path("data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm")
    start = time.monotonic()
    circuit = QuantumCircuit.from_qasm_file(str(source))
    # Use a PyZX-supported exact basis; this is a representation change, not an
    # approximate optimization.
    basis = transpile(circuit, basis_gates=["rz", "sx", "x", "cx"], optimization_level=0)
    qasm = dumps(basis)
    # PyZX 0.10 rejects scientific-notation phase literals; decimal expansion
    # is algebraically identical and keeps the input within its parser grammar.
    qasm = re.sub(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?[eE][-+]?\d+", lambda match: f"{float(match.group()):.17f}", qasm)
    zx_circuit = zx.Circuit.from_qasm(qasm)
    before_2q = sum(gate.name in {"CNOT", "CZ", "CRZ"} for gate in zx_circuit.gates)
    graph = zx.Circuit.to_graph(zx_circuit)
    before_vertices = graph.num_vertices()
    zx.simplify.full_reduce(graph)
    extracted = zx.extract_circuit(graph)
    reduced_qasm = extracted.to_qasm()
    Path("results/p11_final_campaign/p9_pyzx_reduced.qasm").write_text(reduced_qasm)
    after_2q = sum(gate.name in {"CNOT", "CZ", "CRZ"} for gate in extracted.gates)
    output = Path("results/p11_final_campaign/pyzx_results.json")
    payload = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "basis": ["rz", "sx", "x", "cx"],
        "before_2q": before_2q,
        "after_2q": after_2q,
        "before_vertices": before_vertices,
        "after_gates": len(extracted.gates),
        "reduced_qasm": "results/p11_final_campaign/p9_pyzx_reduced.qasm",
        "equivalence": "exact_graph_rewrite",
        "runtime_s": time.monotonic() - start,
        "verdict": "MATERIAL_REDUCTION" if after_2q < before_2q else "NO_MATERIAL_REDUCTION",
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
