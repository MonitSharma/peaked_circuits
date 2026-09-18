"""Bounded finite-horizon routing beam over projected interaction debt."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BeamState:
    order: tuple[int, ...]
    score: float
    swaps: tuple[int, ...]


def _debt(order: tuple[int, ...], pairs: tuple[tuple[int, int], ...]) -> float:
    positions = {logical: site for site, logical in enumerate(order)}
    return float(sum(abs(positions[a] - positions[b]) for a, b in pairs))


def finite_horizon_beam(n_qubits: int, pairs: tuple[tuple[int, int], ...], *, width: int, depth: int) -> tuple[BeamState, ...]:
    """Search adjacent virtual swaps using future projected routing debt only."""
    beam = (BeamState(tuple(range(n_qubits)), 0.0, ()),)
    for step in range(depth):
        future = pairs[step : step + depth + 1]
        proposals: list[BeamState] = []
        for state in beam:
            candidates = [None]
            if future:
                a, b = min(future, key=lambda pair: abs(state.order.index(pair[0]) - state.order.index(pair[1])))
                left, right = sorted((state.order.index(a), state.order.index(b)))
                candidates.extend(site for site in (left - 1, left, right - 1, right) if 0 <= site < n_qubits - 1)
            for site in dict.fromkeys(candidates):
                order = list(state.order)
                swaps = state.swaps
                if site is not None:
                    order[site], order[site + 1] = order[site + 1], order[site]
                    swaps = (*swaps, site)
                score = _debt(tuple(order), future) + 0.05 * len(swaps)
                proposals.append(BeamState(tuple(order), score, swaps))
        beam = tuple(sorted(proposals, key=lambda state: (state.score, state.swaps))[:width])
    return beam
