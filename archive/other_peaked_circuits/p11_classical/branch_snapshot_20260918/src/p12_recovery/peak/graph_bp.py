"""Positivity- and convergence-checked binary pairwise belief propagation.

This is an environment-aware decoder for supplied graph factors. It is not a
quantum-circuit simulator: target use is blocked unless factors come from a
validated tensor-network environment calculation. Exact enumeration is limited
to small controls and bounded explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BPResult:
    beliefs: np.ndarray
    converged: bool
    iterations: int
    max_message_delta: float


class BinaryPairwiseGraph:
    def __init__(self, unary: np.ndarray, pairwise: dict[tuple[int, int], np.ndarray], *, edges: list[tuple[int, int]] | None = None) -> None:
        self.unary = np.asarray(unary, dtype=float)
        if self.unary.ndim != 2 or self.unary.shape[1] != 2:
            raise ValueError("unary factors must have shape (n, 2)")
        self.n = self.unary.shape[0]
        self.pairwise: dict[tuple[int, int], np.ndarray] = {}
        for edge, factor in pairwise.items():
            left, right = edge
            if left == right or not (0 <= left < self.n and 0 <= right < self.n):
                raise ValueError("pairwise edge is out of range")
            key = (min(left, right), max(left, right))
            matrix = np.asarray(factor, dtype=float)
            if matrix.shape != (2, 2) or not np.all(np.isfinite(matrix)) or np.any(matrix <= 0):
                raise ValueError("pairwise factors must be finite and strictly positive 2x2 matrices")
            self.pairwise[key] = matrix if edge == key else matrix.T
        if not np.all(np.isfinite(self.unary)) or np.any(self.unary <= 0):
            raise ValueError("unary factors must be finite and strictly positive")
        self.neighbors = {node: set() for node in range(self.n)}
        for left, right in self.pairwise:
            self.neighbors[left].add(right)
            self.neighbors[right].add(left)
        if edges is not None and {tuple(sorted(edge)) for edge in edges} != set(self.pairwise):
            raise ValueError("edges must agree with pairwise factors")

    def _factor(self, left: int, right: int) -> np.ndarray:
        matrix = self.pairwise[(min(left, right), max(left, right))]
        return matrix if left < right else matrix.T

    def sum_product(self, *, max_iter: int = 200, tolerance: float = 1e-10, damping: float = 0.0) -> BPResult:
        if not 0 <= damping < 1:
            raise ValueError("damping must lie in [0, 1)")
        messages = {(left, right): np.ones(2) / 2 for left, right in self._directed_edges()}
        delta = float("inf")
        for iteration in range(1, max_iter + 1):
            updated = {}
            for left, right in messages:
                incoming = self.unary[left].copy()
                for neighbor in self.neighbors[left] - {right}:
                    incoming *= messages[(neighbor, left)]
                value = incoming @ self._factor(left, right)
                value /= value.sum()
                updated[(left, right)] = damping * messages[(left, right)] + (1 - damping) * value
            delta = max(float(np.max(np.abs(updated[key] - messages[key]))) for key in messages) if messages else 0.0
            messages = updated
            if delta <= tolerance:
                return BPResult(self._beliefs(messages), True, iteration, delta)
        return BPResult(self._beliefs(messages), False, max_iter, delta)

    def _beliefs(self, messages: dict[tuple[int, int], np.ndarray]) -> np.ndarray:
        beliefs = np.empty((self.n, 2), dtype=float)
        for node in range(self.n):
            belief = self.unary[node].copy()
            for neighbor in self.neighbors[node]:
                belief *= messages[(neighbor, node)]
            beliefs[node] = belief / belief.sum()
        return beliefs

    def _directed_edges(self) -> list[tuple[int, int]]:
        return [(left, right) for left, right in self.pairwise for left, right in ((left, right), (right, left))]

    def top_k(self, *, k: int = 32, max_states: int = 1_048_576) -> list[dict[str, Any]]:
        if self.n > 20 or 2**self.n > max_states:
            raise ValueError("exact graph top-k is limited to at most 20 qubits")
        rows = []
        for index in range(2**self.n):
            bits = format(index, f"0{self.n}b")
            score = float(np.prod(self.unary[np.arange(self.n), [int(bit) for bit in bits]]))
            for left, right in self.pairwise:
                score *= self.pairwise[(left, right)][int(bits[left]), int(bits[right])]
            rows.append({"bitstring": bits, "unnormalized_score": score})
        rows.sort(key=lambda row: (-row["unnormalized_score"], row["bitstring"]))
        total = sum(row["unnormalized_score"] for row in rows)
        for row in rows[:k]:
            row["probability"] = row["unnormalized_score"] / total
        return rows[:k]
