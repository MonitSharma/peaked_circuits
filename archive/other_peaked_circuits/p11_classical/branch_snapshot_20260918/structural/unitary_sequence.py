"""Temporal alignment of continuous one-qubit unitary sequences."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from .patch_unitary import phase_insensitive_fidelity


def dtw_similarity(
    left: list[np.ndarray],
    right: list[np.ndarray],
    *,
    adjoint_left: bool = True,
    gap_penalty: float = -0.25,
) -> float:
    """Monotone alignment score, normalized by the resulting path length."""
    if not left or not right:
        return 0.0
    local = np.asarray(
        [
            [
                phase_insensitive_fidelity(
                    left_matrix.conj().T if adjoint_left else left_matrix, right_matrix
                )
                for right_matrix in right
            ]
            for left_matrix in left
        ],
        dtype=np.float64,
    )
    dynamic = np.full((len(left) + 1, len(right) + 1), -np.inf, dtype=np.float64)
    lengths = np.zeros((len(left) + 1, len(right) + 1), dtype=np.int32)
    dynamic[0, 0] = 0.0
    for i in range(1, len(left) + 1):
        for j in range(1, len(right) + 1):
            candidates = [
                (dynamic[i - 1, j] + gap_penalty, lengths[i - 1, j] + 1),
                (dynamic[i, j - 1] + gap_penalty, lengths[i, j - 1] + 1),
                (dynamic[i - 1, j - 1] + local[i - 1, j - 1], lengths[i - 1, j - 1] + 1),
            ]
            best = max(candidates, key=lambda item: item[0] / item[1])
            dynamic[i, j], lengths[i, j] = best
    return float(dynamic[-1, -1] / lengths[-1, -1])


@dataclass(frozen=True)
class UnitarySequenceAssignment:
    permutation: tuple[int, ...]
    score: float
    compatibility: np.ndarray


def sequence_assignment(
    left: list[list[np.ndarray]], right: list[list[np.ndarray]], *, adjoint_left: bool = True
) -> UnitarySequenceAssignment:
    if len(left) != len(right):
        raise ValueError("left and right sequence collections must have equal width")
    compatibility = np.asarray(
        [
            [dtw_similarity(a, b, adjoint_left=adjoint_left) for b in right]
            for a in left
        ],
        dtype=np.float64,
    )
    rows, columns = linear_sum_assignment(-compatibility)
    permutation = np.full(len(left), -1, dtype=int)
    permutation[rows] = columns
    return UnitarySequenceAssignment(
        tuple(int(value) for value in permutation),
        float(compatibility[rows, columns].mean()),
        compatibility,
    )
