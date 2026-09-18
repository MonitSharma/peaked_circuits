"""Aggregated temporal interaction graphs and bounded graph matching."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from .qasm_events import CircuitEvents


def interaction_matrix(circuit: CircuitEvents, start: int, stop: int) -> np.ndarray:
    matrix = np.zeros((circuit.n_qubits, circuit.n_qubits), dtype=np.float64)
    for event in circuit.window(start, stop):
        first, second = event.wires
        matrix[first, second] += 1.0
        matrix[second, first] += 1.0
    return matrix


def layer_interaction_matrix(circuit: CircuitEvents, start: int, stop: int) -> np.ndarray:
    matrix = np.zeros((circuit.n_qubits, circuit.n_qubits), dtype=np.float64)
    for event in circuit.two_qubit:
        if start <= event.layer < stop:
            first, second = event.wires
            matrix[first, second] += 1.0
            matrix[second, first] += 1.0
    return matrix


def graph_agreement(left: np.ndarray, right: np.ndarray, permutation: np.ndarray) -> float:
    mapped = right[np.ix_(permutation, permutation)]
    denominator = float(np.linalg.norm(left) * np.linalg.norm(mapped))
    return float(np.sum(left * mapped) / denominator) if denominator else 0.0


def spectral_assignment(left: np.ndarray, right: np.ndarray, *, components: int = 8) -> np.ndarray:
    left_values, left_vectors = np.linalg.eigh(left)
    right_values, right_vectors = np.linalg.eigh(right)
    count = min(components, left.shape[0])
    left_embedding = np.abs(left_vectors[:, -count:]) * np.sqrt(np.abs(left_values[-count:]))
    right_embedding = np.abs(right_vectors[:, -count:]) * np.sqrt(np.abs(right_values[-count:]))
    cost = np.mean((left_embedding[:, None, :] - right_embedding[None, :, :]) ** 2, axis=2)
    rows, columns = linear_sum_assignment(cost)
    permutation = np.full(left.shape[0], -1, dtype=int)
    permutation[rows] = columns
    return permutation


def refine_by_transpositions(
    left: np.ndarray, right: np.ndarray, permutation: np.ndarray, *, passes: int = 3
) -> tuple[np.ndarray, list[float]]:
    permutation = np.asarray(permutation, dtype=int).copy()
    history = [graph_agreement(left, right, permutation)]
    for _ in range(passes):
        best_score = history[-1]
        best_pair: tuple[int, int] | None = None
        for first in range(len(permutation)):
            for second in range(first + 1, len(permutation)):
                proposal = permutation.copy()
                proposal[first], proposal[second] = proposal[second], proposal[first]
                score = graph_agreement(left, right, proposal)
                if score > best_score + 1e-12:
                    best_score, best_pair = score, (first, second)
        if best_pair is None:
            break
        first, second = best_pair
        permutation[first], permutation[second] = permutation[second], permutation[first]
        history.append(best_score)
    return permutation, history
