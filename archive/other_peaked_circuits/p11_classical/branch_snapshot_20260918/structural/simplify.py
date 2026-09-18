"""Exact, provenance-preserving local simplifications for event streams."""

from __future__ import annotations

import numpy as np

from .patch_unitary import gate_matrix
from .qasm_events import Event


def cancel_adjacent_inverses(
    events: list[Event], *, tolerance: float = 1e-9
) -> tuple[list[Event], list[dict[str, object]]]:
    kept: list[Event] = []
    cancellations: list[dict[str, object]] = []
    for event in events:
        if kept and kept[-1].wires == event.wires and kept[-1].gate == event.gate:
            product = gate_matrix(event) @ gate_matrix(kept[-1])
            if np.allclose(product, np.eye(product.shape[0]), atol=tolerance):
                previous = kept.pop()
                cancellations.append(
                    {
                        "removed_indices": [previous.index, event.index],
                        "gate": event.gate,
                        "wires": list(event.wires),
                        "type": "exact_inverse",
                    }
                )
                continue
        kept.append(event)
    return kept, cancellations
