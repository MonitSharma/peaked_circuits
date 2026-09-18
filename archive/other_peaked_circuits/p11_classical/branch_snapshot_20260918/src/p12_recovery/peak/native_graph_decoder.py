"""Correlation-aware sequential beam decoding for a native graph state."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .native_graph_state import NativeGraphState


@dataclass
class BeamCandidate:
    bits: dict[int, int]
    state: NativeGraphState
    weight: float


def decode_graph_state(state: NativeGraphState, beam_width: int = 32) -> list[dict[str, object]]:
    """Decode correlated peaks by projection, regauging, and beam pruning.

    ``weight`` is the projected squared norm divided by the root squared norm.
    The returned bitstrings are in original logical-qubit order. This is a
    decoder for the approximate graph state, not an exact-circuit certificate.
    """
    if beam_width < 1:
        raise ValueError("beam_width must be positive")
    root_norm = state.norm()
    remaining = set(range(state.graph.n_qubits))
    # A deterministic geometry-aware order: expose high-degree variables first.
    order = sorted(remaining, key=lambda q: (-state.graph_degree(q), q))
    beam = [BeamCandidate({}, state, root_norm)]
    for qubit in order:
        expanded: list[BeamCandidate] = []
        for candidate in beam:
            for bit in (0, 1):
                child = candidate.state.project_bit(qubit, bit)
                weight = child.norm()
                if np.isfinite(weight) and weight > 0.0:
                    expanded.append(BeamCandidate({**candidate.bits, qubit: bit}, child, weight))
        expanded.sort(key=lambda c: (-c.weight, tuple(c.bits[q] for q in order if q in c.bits)))
        beam = expanded[:beam_width]
        if not beam:
            break
        remaining.discard(qubit)
    out = []
    for candidate in beam:
        bits = "".join(str(candidate.bits[q]) for q in range(state.graph.n_qubits))
        out.append({"bitstring": bits, "probability": candidate.weight / root_norm,
                    "projected_norm": candidate.weight, "beam_width": beam_width})
    return out
