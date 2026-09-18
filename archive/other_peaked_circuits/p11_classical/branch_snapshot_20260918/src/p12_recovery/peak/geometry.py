"""P8 geometry diagnostics; no geometry-aware recovery claim is made here."""

from __future__ import annotations

from collections import defaultdict

from .qasm import PeakQASM


def interaction_geometry(circuit: PeakQASM) -> dict:
    neighbors: dict[int, set[int]] = defaultdict(set)
    for gate in circuit.gates:
        if len(gate.qubits) == 2:
            a, b = gate.qubits
            neighbors[a].add(b)
            neighbors[b].add(a)
    degree = [len(neighbors[q]) for q in range(circuit.n_qubits)]
    return {"n_qubits": circuit.n_qubits, "unique_edges": sum(len(v) for v in neighbors.values()) // 2, "degree_min": min(degree, default=0), "degree_max": max(degree, default=0), "degree_mean": sum(degree) / len(degree) if degree else 0.0, "geometry_path_status": "DIAGNOSTIC_ONLY", "answer_blind": True}
