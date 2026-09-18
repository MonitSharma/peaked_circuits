#!/usr/bin/env python3
"""Export a canonical, answer-blind QASM gate stream for PPS experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit


NATIVE = {
    "h": "CliffordGate:H",
    "x": "CliffordGate:X",
    "y": "CliffordGate:Y",
    "z": "CliffordGate:Z",
    "s": "CliffordGate:S",
    "sdg": "CliffordGate:SDG",
    "sx": "CliffordGate:SX",
    "sxdg": "CliffordGate:SXDG",
    "cx": "CliffordGate:CNOT",
    "cz": "CliffordGate:CZ",
    "swap": "CliffordGate:SWAP",
    "t": "TGate",
    "tdg": "TGate:inverse",
    "rx": "PauliRotation:RX",
    "ry": "PauliRotation:RY",
    "rz": "PauliRotation:RZ",
    "rzz": "PauliRotation:RZZ",
}

ROTATIONS = {"rx", "ry", "rz", "rxx", "ryy", "rzz"}
CLIFFORD = {"h", "x", "y", "z", "s", "sdg", "sx", "sxdg", "cx", "cz", "swap"}


def qindex(circuit: QuantumCircuit, bit: Any) -> int:
    return int(circuit.find_bit(bit).index)


def json_matrix(operation: Any) -> list[list[list[float]]]:
    matrix = operation.to_matrix()
    return [[[float(value.real), float(value.imag)] for value in row] for row in matrix]


def numeric_parameter(value: Any) -> float | str:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return str(value)
    return result if math.isfinite(result) else str(value)


def canonical_stream(circuit: QuantumCircuit) -> list[dict[str, Any]]:
    stream: list[dict[str, Any]] = []
    for instruction_index, item in enumerate(circuit.data):
        operation = item.operation
        if operation.name in {"barrier", "measure", "reset", "delay"}:
            continue
        qargs = [qindex(circuit, bit) for bit in item.qubits]
        parameters = [numeric_parameter(value) for value in operation.params]
        native = NATIVE.get(operation.name)
        fallback = None if native else "TransferMapGate"
        record: dict[str, Any] = {
            "instruction_index": instruction_index,
            "gate_name": operation.name,
            "qargs_qiskit_zero_based": qargs,
            "qargs_julia_one_based": [value + 1 for value in qargs],
            "parameters": parameters,
            "native_pps_mapping": native,
            "fallback": fallback,
        }
        if fallback is not None:
            record["matrix_01_basis"] = json_matrix(operation)
        stream.append(record)
    return stream


def audit(circuit: QuantumCircuit, stream: list[dict[str, Any]], qasm: Path) -> dict[str, Any]:
    gate_counts = Counter(record["gate_name"] for record in stream)
    one_qubit = sum(len(record["qargs_qiskit_zero_based"]) == 1 for record in stream)
    two_qubit = sum(len(record["qargs_qiskit_zero_based"]) == 2 for record in stream)
    angle_counts: Counter[str] = Counter()
    for record in stream:
        if record["gate_name"] in ROTATIONS and record["parameters"]:
            angle_counts[str(record["parameters"][0])] += 1
    degrees: Counter[int] = Counter()
    for record in stream:
        qargs = record["qargs_qiskit_zero_based"]
        if len(qargs) == 2:
            left, right = qargs
            degrees[left] += 1
            degrees[right] += 1
    native_count = sum(record["native_pps_mapping"] is not None for record in stream)
    fallback_count = len(stream) - native_count
    nonclifford = sum(record["gate_name"] not in CLIFFORD for record in stream)
    occupied = [0] * circuit.num_qubits
    clifford_depth = 0
    magic_depth = 0
    for record in stream:
        qargs = record["qargs_qiskit_zero_based"]
        layer = 1 + max((occupied[q] for q in qargs), default=0)
        for q in qargs:
            occupied[q] = layer
        if record["gate_name"] in CLIFFORD:
            clifford_depth = max(clifford_depth, layer)
        else:
            magic_depth = max(magic_depth, layer)
    return {
        "qasm": str(qasm),
        "qasm_sha256": hashlib.sha256(qasm.read_bytes()).hexdigest(),
        "num_qubits": circuit.num_qubits,
        "instruction_count_excluding_measurements": len(stream),
        "total_gate_count_from_qiskit": len(circuit.data),
        "one_qubit_gate_count": int(one_qubit),
        "two_qubit_gate_count": int(two_qubit),
        "gate_alphabet": dict(sorted(gate_counts.items())),
        "parameterized_gate_alphabet": dict(sorted((name, count) for name, count in gate_counts.items() if name in ROTATIONS)),
        "clifford_gate_count": int(len(stream) - nonclifford),
        "nonclifford_or_parameterized_gate_count": int(nonclifford),
        "estimated_clifford_depth": int(clifford_depth),
        "estimated_nonclifford_or_magic_depth": int(magic_depth),
        "distinct_rotation_angles": len(angle_counts),
        "rotation_angle_frequencies": dict(sorted(angle_counts.items(), key=lambda item: (-item[1], item[0]))),
        "interaction_graph_degree": {str(key): value for key, value in sorted(degrees.items())},
        "interaction_graph_max_degree": max(degrees.values(), default=0),
        "native_pps_mapping_count": native_count,
        "generic_transfer_map_fallback_count": fallback_count,
        "potential_pauli_branching_gate_count": sum(record["gate_name"] in ROTATIONS for record in stream),
        "measurement_count": sum(item.operation.name == "measure" for item in circuit.data),
        "canonical_qargs_mapping": "q_julia = q_qiskit + 1",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--stream", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    qasm = args.qasm.resolve()
    circuit = QuantumCircuit.from_qasm_file(str(qasm))
    stream = canonical_stream(circuit)
    payload = {
        "schema": "p11_pps_canonical_gate_stream_v1",
        "qasm_sha256": hashlib.sha256(qasm.read_bytes()).hexdigest(),
        "num_qubits": circuit.num_qubits,
        "measurement_order_qiskit": [
            {"clbit": circuit.find_bit(bit).index, "qubit": circuit.find_bit(item.qubits[0]).index}
            for item in circuit.data
            if item.operation.name == "measure"
            for bit in item.clbits
        ],
        "gates": stream,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["canonical_stream_sha256"] = hashlib.sha256(canonical).hexdigest()
    args.stream.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.stream.write_text(json.dumps(payload, indent=2) + "\n")
    args.audit.write_text(json.dumps(audit(circuit, stream, qasm), indent=2) + "\n")
    print(json.dumps({"stream": str(args.stream), "audit": str(args.audit), **audit(circuit, stream, qasm)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
