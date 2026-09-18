from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from .hashing import sha256_file
from .interaction_graph import build_interaction_graph, interaction_statistics
from .models import CircuitInspectionReport, GateStatistics
from .qasm_io import ParsedQASM, load_qasm
from .reporting import package_versions

KNOWN_GATES = {
    "u",
    "u1",
    "u2",
    "u3",
    "x",
    "y",
    "z",
    "h",
    "s",
    "sdg",
    "t",
    "tdg",
    "rx",
    "ry",
    "rz",
    "cx",
    "cz",
    "cy",
    "ch",
    "swap",
    "ccx",
    "barrier",
    "reset",
    "measure",
    "id",
}


def _depth(circuit: ParsedQASM, arity: int | None = None) -> int:
    levels = [0] * circuit.number_of_qubits
    maximum = 0
    for operation in circuit.operations:
        if operation.name in {"barrier", "measure"}:
            continue
        if arity is not None and len(operation.qubits) != arity:
            continue
        if not operation.qubits:
            continue
        level = max(levels[q] for q in operation.qubits) + 1
        for q in operation.qubits:
            levels[q] = level
        maximum = max(maximum, level)
    return maximum


def inspect_circuit(
    path: Path, *, sdk_cross_check: bool = True
) -> tuple[CircuitInspectionReport, ParsedQASM]:
    circuit = load_qasm(path, sdk_cross_check=sdk_cross_check)
    counts = Counter(operation.name for operation in circuit.operations)
    used = sorted({q for operation in circuit.operations for q in operation.qubits})
    measured = sorted(
        {
            q
            for operation in circuit.operations
            if operation.name == "measure"
            for q in operation.qubits
        }
    )
    parameters = [value for operation in circuit.operations for value in operation.parameters]
    unsupported = sorted(set(counts) - KNOWN_GATES)
    gate_stats = GateStatistics(
        total_operations=len(circuit.operations),
        counts_by_gate=dict(sorted(counts.items())),
        one_qubit_gates=sum(
            len(op.qubits) == 1 and op.name not in {"measure", "reset"} for op in circuit.operations
        ),
        two_qubit_gates=sum(len(op.qubits) == 2 for op in circuit.operations),
        greater_than_two_qubit_gates=sum(
            len(op.qubits) > 2 and op.name != "barrier" for op in circuit.operations
        ),
        barriers=counts["barrier"],
        resets=counts["reset"],
        measurements=counts["measure"],
        conditional_operations=sum(op.conditional for op in circuit.operations),
        unsupported_instructions=unsupported,
        circuit_depth=_depth(circuit),
        one_qubit_depth=_depth(circuit, 1),
        two_qubit_depth=_depth(circuit, 2),
    )
    graph_stats = interaction_statistics(build_interaction_graph(circuit))
    report = CircuitInspectionReport(
        circuit_name=path.stem,
        source_path=str(path),
        source_sha256=sha256_file(path),
        qasm_version=circuit.qasm_version,
        parser=circuit.parser,
        parser_version=circuit.parser_version,
        number_of_qubits=circuit.number_of_qubits,
        number_of_classical_bits=circuit.number_of_classical_bits,
        quantum_registers=[
            {"name": r.name, "size": r.size, "offset": r.offset} for r in circuit.quantum_registers
        ],
        classical_registers=[
            {"name": r.name, "size": r.size, "offset": r.offset}
            for r in circuit.classical_registers
        ],
        used_qubits=used,
        unused_qubits=sorted(set(range(circuit.number_of_qubits)) - set(used)),
        measured_qubits=measured,
        unmeasured_qubits=sorted(set(range(circuit.number_of_qubits)) - set(measured)),
        source_contains_measurements=bool(measured),
        gates=gate_stats,
        has_symbolic_parameters=False,
        symbolic_parameter_count=0,
        all_numerical_angles_finite=all(math.isfinite(x) for x in parameters),
        minimum_rotation_angle=min(parameters, default=None),
        maximum_rotation_angle=max(parameters, default=None),
        interaction_graph=graph_stats,
        depth_definition="ASAP scheduling over relevant operations; 1q/2q depth ignore operations of other arities",
        package_versions=package_versions(),
        input_hashes={str(path): sha256_file(path)},
    )
    return report, circuit
