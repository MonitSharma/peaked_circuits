"""Bounded assignment and randomized-null controls."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass(frozen=True)
class Assignment:
    permutation: tuple[int, ...]
    score: float
    margins: tuple[float, ...]


def hungarian(compatibility: np.ndarray) -> Assignment:
    rows, columns = linear_sum_assignment(-compatibility)
    permutation = np.full(compatibility.shape[0], -1, dtype=int)
    permutation[rows] = columns
    selected = compatibility[rows, columns]
    margins = []
    for row, column in zip(rows, columns, strict=True):
        alternatives = np.delete(compatibility[row], column)
        margins.append(float(compatibility[row, column] - alternatives.max(initial=0.0)))
    return Assignment(
        tuple(int(value) for value in permutation), float(selected.mean()), tuple(margins)
    )


def null_scores(compatibility: np.ndarray, *, trials: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    scores = np.empty(trials, dtype=np.float64)
    for index in range(trials):
        permutation = rng.permutation(compatibility.shape[1])
        scores[index] = float(
            np.mean(compatibility[np.arange(compatibility.shape[0]), permutation])
        )
    return scores


def assignment_significance(score: float, null: np.ndarray) -> dict[str, float]:
    mean = float(np.mean(null))
    std = float(np.std(null, ddof=1)) if len(null) > 1 else 0.0
    return {
        "score": score,
        "null_mean": mean,
        "null_std": std,
        "z": (score - mean) / std if std else 0.0,
        "empirical_p": float((1 + np.count_nonzero(null >= score)) / (len(null) + 1)),
    }
