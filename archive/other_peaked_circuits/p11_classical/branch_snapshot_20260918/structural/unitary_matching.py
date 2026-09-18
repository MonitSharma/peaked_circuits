"""Layerwise one-qubit unitary correspondence scores for small local patches."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment

from .patch_unitary import gate_matrix
from .qasm_events import CircuitEvents


def _u_layers(circuit: CircuitEvents) -> dict[int, dict[int, np.ndarray]]:
    layers: dict[int, dict[int, np.ndarray]] = defaultdict(dict)
    for event in circuit.events:
        if event.gate == "u":
            layers[event.layer][event.wires[0]] = gate_matrix(event)
    return layers


def layer_unitary_compatibility(
    circuit: CircuitEvents,
    left_layers: list[int],
    right_layers: list[int],
    *,
    adjoint_right: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate phase-insensitive U-layer similarity and overlap counts."""
    if len(left_layers) != len(right_layers):
        raise ValueError("left/right layer windows must have equal length")
    layers = _u_layers(circuit)
    score_sum = np.zeros((circuit.n_qubits, circuit.n_qubits), dtype=np.float64)
    overlap = np.zeros_like(score_sum)
    for left_layer, right_layer in zip(reversed(left_layers), right_layers, strict=True):
        for left_wire, left_matrix in layers.get(left_layer, {}).items():
            for right_wire, right_matrix in layers.get(right_layer, {}).items():
                if adjoint_right:
                    right_matrix = right_matrix.conj().T
                score_sum[left_wire, right_wire] += abs(np.trace(left_matrix.conj().T @ right_matrix)) / 2.0
                overlap[left_wire, right_wire] += 1.0
    score = np.divide(score_sum, overlap, out=np.zeros_like(score_sum), where=overlap > 0)
    return score, overlap


def unitary_assignment(score: np.ndarray, overlap: np.ndarray) -> tuple[np.ndarray, float, float]:
    rows, columns = linear_sum_assignment(-score)
    permutation = np.full(score.shape[0], -1, dtype=int)
    permutation[rows] = columns
    selected = score[rows, columns]
    support = overlap[rows, columns]
    return permutation, float(selected.mean()), float(support.mean())
