"""Windowed, label-agnostic temporal fingerprints for hidden-correspondence recovery."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

import numpy as np

from .qasm_events import CircuitEvents, Event


@dataclass(frozen=True)
class WindowFingerprint:
    start: int
    stop: int
    direction: str
    values: np.ndarray


def _param_bucket(params: tuple[float, ...]) -> int:
    payload = ",".join(f"{value:.7g}" for value in params).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:2], "big") % 16


def _one_q_counts(
    circuit: CircuitEvents, start_layer: int, stop_layer: int, qubit: int
) -> tuple[int, ...]:
    counts = [0] * 16
    for event in circuit.events:
        if (
            event.gate == "u"
            and event.wires[0] == qubit
            and start_layer <= event.layer < stop_layer
        ):
            counts[_param_bucket(event.params)] += 1
    return tuple(counts)


def _qubit_vector(
    circuit: CircuitEvents, events: tuple[Event, ...], qubit: int, reverse: bool
) -> np.ndarray:
    positions: list[int] = []
    gate_counts = Counter()
    gaps: list[int] = []
    for position, event in enumerate(events):
        if qubit in event.wires:
            positions.append(position)
            gate_counts[event.gate] += 1
            if len(positions) > 1:
                gaps.append(positions[-1] - positions[-2])
    n = max(1, len(events))
    sequence = [event.gate for event in events if qubit in event.wires]
    if reverse:
        sequence = list(reversed(sequence))
    seq_hash = (
        int.from_bytes(hashlib.sha256("|".join(sequence).encode()).digest()[:4], "big") / 2**32
    )
    if positions:
        first, last = positions[0] / n, positions[-1] / n
    else:
        first = last = 1.0
    values = [
        len(positions) / n,
        gate_counts["cz"] / n,
        gate_counts["rzz"] / n,
        first,
        last,
        float(np.mean(gaps)) / n if gaps else 1.0,
        float(np.std(gaps)) / n if gaps else 0.0,
        seq_hash,
    ]
    layer_start = min((event.layer for event in events), default=0)
    layer_stop = max((event.layer for event in events), default=layer_start) + 1
    values.extend(
        count / max(1, len(events))
        for count in _one_q_counts(circuit, layer_start, layer_stop, qubit)
    )
    return np.asarray(values, dtype=np.float64)


def window_fingerprints(
    circuit: CircuitEvents, start: int, stop: int, *, reverse: bool = False
) -> np.ndarray:
    """Return one feature row per logical qubit for a 2q-event window."""
    events = circuit.window(start, stop)
    if reverse:
        events = tuple(reversed(events))
    return np.vstack(
        [_qubit_vector(circuit, events, qubit, reverse) for qubit in range(circuit.n_qubits)]
    )


def layer_fingerprints(
    circuit: CircuitEvents, start: int, stop: int, *, reverse: bool = False
) -> np.ndarray:
    """Fingerprint events in a circuit-layer window instead of a 2q-count window."""
    events = tuple(event for event in circuit.two_qubit if start <= event.layer < stop)
    if reverse:
        events = tuple(reversed(events))
    return np.vstack(
        [_qubit_vector(circuit, events, qubit, reverse) for qubit in range(circuit.n_qubits)]
    )


def compatibility(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Feature-wise Gaussian similarity matrix, robust to scale differences."""
    if left.shape[1] != right.shape[1]:
        raise ValueError("fingerprint dimensions differ")
    pooled = np.vstack((left, right))
    scale = np.std(pooled, axis=0)
    scale[scale < 1e-9] = 1.0
    delta = (left[:, None, :] - right[None, :, :]) / scale
    return np.exp(-0.5 * np.mean(delta * delta, axis=2))
