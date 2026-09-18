"""Answer-blind MPS MAP decoding and exact small gate fixtures."""

from __future__ import annotations

import heapq
import time
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


def iswap_matrix(dtype=np.complex128) -> np.ndarray:
    return np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]], dtype=dtype)


@dataclass(frozen=True)
class MAPResult:
    bitstring: str | None
    probability: float
    certified: bool
    nodes_expanded: int
    max_queue_size: int
    final_upper_bound: float
    runner_up: tuple[str, float] | None
    wall_time_s: float


def _normal_forms(mps: Sequence[np.ndarray]) -> list[np.ndarray]:
    """Normalize common open-boundary MPS tensor shapes to (left, physical, right)."""
    out = []
    for i, tensor in enumerate(mps):
        a = np.asarray(tensor)
        if a.ndim == 2:
            if i == 0:
                a = a.reshape(1, *a.shape)
            elif i == len(mps) - 1:
                a = a.reshape(1, *a.shape)
            else:
                raise ValueError("interior MPS tensors must have three axes")
        if a.ndim != 3 or a.shape[1] != 2:
            raise ValueError("MPS tensors must have shape (left, 2, right)")
        out.append(a)
    return out


def best_first_map(mps: Sequence[np.ndarray], *, max_nodes: int | None = None,
                   max_seconds: float | None = None) -> MAPResult:
    """Best-first MAP with a completion-mass upper bound.

    The queue key is the norm of the current prefix vector.  For a right
    canonical normalized MPS this is the exact probability mass of all
    completions of that prefix.  Certification is therefore reported only when
    all queued prefixes are bounded by the incumbent complete assignment.
    """
    tensors = _normal_forms(mps)
    started = time.monotonic()
    queue: list[tuple[float, int, str, np.ndarray]] = []
    root = np.ones(1, dtype=np.result_type(*[a.dtype for a in tensors]))
    counter = 0
    heapq.heappush(queue, (-1.0, counter, "", root))
    best: tuple[str, float] | None = None
    second: tuple[str, float] | None = None
    expanded = 0
    max_queue = 1
    while queue:
        if max_nodes is not None and expanded >= max_nodes:
            break
        if max_seconds is not None and time.monotonic() - started >= max_seconds:
            break
        neg_bound, _, prefix, vector = heapq.heappop(queue)
        bound = -neg_bound
        if best is not None and bound <= best[1] + 1e-15:
            # All remaining entries have no better bound because the heap is ordered.
            return MAPResult(best[0], best[1], True, expanded, max_queue, bound, second, time.monotonic() - started)
        expanded += 1
        if len(prefix) == len(tensors):
            prob = float(np.vdot(vector, vector).real)
            if best is None or prob > best[1]:
                second = best
                best = (prefix, prob)
            elif second is None or prob > second[1]:
                second = (prefix, prob)
            continue
        i = len(prefix)
        tensor = tensors[i]
        for bit in (0, 1):
            child = vector @ tensor[:, bit, :]
            child_bound = float(np.vdot(child, child).real)
            counter += 1
            heapq.heappush(queue, (-child_bound, counter, prefix + str(bit), child))
        max_queue = max(max_queue, len(queue))
    final_bound = -queue[0][0] if queue else 0.0
    return MAPResult(best[0] if best else None, best[1] if best else 0.0, False, expanded, max_queue, final_bound, second, time.monotonic() - started)
