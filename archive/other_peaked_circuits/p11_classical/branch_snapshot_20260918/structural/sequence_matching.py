"""Bounded label-agnostic matching for ordered two-qubit interaction streams."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SequenceAssignment:
    """A permutation mapping left-wire labels to right-wire labels."""

    permutation: tuple[int, ...]
    score: float
    passes: int


def edge_agreement(
    left_edges: np.ndarray, right_edges: np.ndarray, permutation: np.ndarray
) -> float:
    """Return the fraction of ordered edge positions preserved by ``permutation``."""
    left_edges = np.asarray(left_edges, dtype=int)
    right_edges = np.asarray(right_edges, dtype=int)
    if left_edges.shape != right_edges.shape or left_edges.ndim != 2 or left_edges.shape[1] != 2:
        raise ValueError("edge streams must both have shape (n, 2)")
    mapped = np.asarray(permutation, dtype=int)[left_edges]
    mapped.sort(axis=1)
    target = np.sort(right_edges.copy(), axis=1)
    return float(np.mean(np.all(mapped == target, axis=1))) if len(left_edges) else 0.0


def sequence_assignment(
    left_edges: np.ndarray,
    right_edges: np.ndarray,
    *,
    n_qubits: int,
    seed: int = 0,
    restarts: int = 8,
    max_passes: int = 8,
) -> SequenceAssignment:
    """Optimize ordered edge agreement with bounded random-restart hill climbing.

    This is deliberately a small diagnostic matcher, not an exhaustive QAP solver.
    Every proposal is a transposition, making the search reproducible and cheap
    enough for windowed null controls.
    """
    left_edges = np.asarray(left_edges, dtype=int)
    right_edges = np.asarray(right_edges, dtype=int)
    if left_edges.shape != right_edges.shape:
        raise ValueError("left and right edge streams must have equal shape")
    rng = np.random.default_rng(seed)
    source = np.asarray(left_edges, dtype=int)
    target = np.sort(right_edges.copy(), axis=1)
    affected_by_wire = [
        np.flatnonzero((source[:, 0] == wire) | (source[:, 1] == wire))
        for wire in range(n_qubits)
    ]

    def mapped_codes(permutation: np.ndarray) -> np.ndarray:
        mapped = permutation[source]
        mapped.sort(axis=1)
        return mapped[:, 0] * n_qubits + mapped[:, 1]

    target_codes = target[:, 0] * n_qubits + target[:, 1]
    best_score = -1.0
    best_permutation = np.arange(n_qubits, dtype=int)
    best_passes = 0
    for _restart in range(max(1, restarts)):
        permutation = rng.permutation(n_qubits)
        codes = mapped_codes(permutation)
        matches = codes == target_codes
        current = float(np.mean(matches)) if len(matches) else 0.0
        completed = 0
        for pass_index in range(max(1, max_passes)):
            completed = pass_index + 1
            improved = False
            order = rng.permutation(n_qubits)
            for first_position, first in enumerate(order[:-1]):
                for second in order[first_position + 1 :]:
                    affected = np.union1d(affected_by_wire[first], affected_by_wire[second])
                    if len(affected) == 0:
                        continue
                    proposal = permutation.copy()
                    first_value, second_value = proposal[first], proposal[second]
                    proposal[first], proposal[second] = second_value, first_value
                    proposed_edges = proposal[source[affected]]
                    proposed_edges.sort(axis=1)
                    proposed_matches = (
                        proposed_edges[:, 0] * n_qubits + proposed_edges[:, 1]
                    ) == target_codes[affected]
                    score = float(
                        (matches.sum() - matches[affected].sum() + proposed_matches.sum())
                        / len(matches)
                    ) if len(matches) else 0.0
                    if score > current + 1e-12:
                        permutation, current = proposal, score
                        codes[affected] = proposed_edges[:, 0] * n_qubits + proposed_edges[:, 1]
                        matches[affected] = proposed_matches
                        improved = True
            if not improved:
                break
        if current > best_score:
            best_score = current
            best_permutation = permutation.copy()
            best_passes = completed + 1
    return SequenceAssignment(
        tuple(int(value) for value in best_permutation), best_score, best_passes
    )
