"""Answer-blind structural probes used to select P5/P6 methods."""

from __future__ import annotations

import numpy as np

from structural.sequence_matching import sequence_assignment

from .qasm import PeakQASM


def mirror_probe(circuit: PeakQASM, *, seed: int = 0) -> dict:
    edges = np.asarray([sorted(g.qubits) for g in circuit.gates if len(g.qubits) == 2], dtype=int)
    if len(edges) < 2:
        return {"status": "INCONCLUSIVE", "edges": len(edges)}
    midpoint = len(edges) // 2
    left = edges[:midpoint]
    right = edges[-midpoint:][::-1]
    assignment = sequence_assignment(left, right, n_qubits=circuit.n_qubits, seed=seed, restarts=4, max_passes=4)
    direct = float(np.mean(np.all(left == right, axis=1))) if len(left) else 0.0
    status = "MIRROR_STRONG_PERMUTED" if assignment.score >= 0.8 and assignment.score > direct + 0.05 else "MIRROR_STRONG_DIRECT" if direct >= 0.8 else "MIRROR_WEAK"
    return {"status": status, "edge_count": len(edges), "midpoint": midpoint, "direct_agreement": direct, "permuted_agreement": assignment.score, "permutation": list(assignment.permutation), "answer_blind": True}


def weighted_backbone(circuit: PeakQASM) -> dict:
    counts: dict[tuple[int, int], int] = {}
    for gate in circuit.gates:
        if len(gate.qubits) == 2:
            pair = tuple(sorted(gate.qubits))
            counts[pair] = counts.get(pair, 0) + 1
    edges = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {"weighted_edges": [{"qubits": list(pair), "count": count} for pair, count in edges], "top_edge_count": edges[0][1] if edges else 0, "answer_blind": True}
