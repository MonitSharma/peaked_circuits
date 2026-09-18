"""Small beam tracker for piecewise hidden permutations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass(frozen=True)
class PermutationState:
    permutation: tuple[int, ...]
    structural_score: float
    transition_cost: float
    total_score: float
    backpointer: int | None


def _assignment_candidates(matrix: np.ndarray, limit: int) -> list[np.ndarray]:
    rows, cols = linear_sum_assignment(-matrix)
    base = np.full(matrix.shape[0], -1, dtype=int)
    base[rows] = cols
    candidates = [base]
    # Keep the proposal set cheap: local swaps around the optimal assignment
    # model the sparse transpositions allowed by the tracker.
    for i in range(matrix.shape[0]):
        for j in range(i + 1, min(matrix.shape[0], i + 5)):
            proposal = base.copy()
            proposal[i], proposal[j] = proposal[j], proposal[i]
            candidates.append(proposal)
            if len(candidates) >= limit:
                return candidates
    return candidates


def track(
    compatibilities: list[np.ndarray], *, beam_width: int, transition_penalty: float
) -> list[PermutationState]:
    if not compatibilities or beam_width < 1:
        return []
    beam: list[PermutationState] = []
    history: list[list[PermutationState]] = []
    for time, matrix in enumerate(compatibilities):
        next_states: list[PermutationState] = []
        proposals = _assignment_candidates(matrix, max(beam_width, 8))
        if time == 0:
            for proposal in proposals[:beam_width]:
                score = float(np.mean(matrix[np.arange(len(proposal)), proposal]))
                next_states.append(PermutationState(tuple(proposal), score, 0.0, score, None))
        else:
            for previous_index, previous in enumerate(beam):
                for proposal in proposals:
                    structural = float(np.mean(matrix[np.arange(len(proposal)), proposal]))
                    changed = float(np.count_nonzero(np.asarray(previous.permutation) != proposal))
                    total = (
                        previous.total_score
                        + structural
                        - transition_penalty * changed / len(proposal)
                    )
                    next_states.append(
                        PermutationState(
                            tuple(proposal), structural, changed, total, previous_index
                        )
                    )
        next_states.sort(key=lambda state: state.total_score, reverse=True)
        beam = next_states[:beam_width]
        history.append(beam)
    if not beam:
        return []
    # Return the winning path in chronological order, preserving backpointer
    # evidence for downstream reporting.
    path = [beam[0]]
    for states in reversed(history[:-1]):
        pointer = path[-1].backpointer
        path.append(states[pointer or 0])
    return list(reversed(path))
