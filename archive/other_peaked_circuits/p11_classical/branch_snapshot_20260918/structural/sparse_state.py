"""Bounded top-K state-vector evolution for the optional P9-only experiment."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from .patch_unitary import gate_matrix
from .qasm_events import CircuitEvents, Event


@dataclass(frozen=True)
class SparseRun:
    retained_probability: float
    discarded_probability: float
    steps: int
    elapsed_s: float
    timed_out: bool


class TopKSparseState:
    """Sparse state retaining at most K computational-basis amplitudes.

    The support is kept sorted and one-qubit updates are performed by pairing
    basis states across the acted-on bit. Diagonal ``cz``/``rzz`` gates do not
    change support. The state is renormalized after every truncation so the
    reported target probability is conditional on retained support.
    """

    def __init__(self, n_qubits: int, retained: int):
        if not 1 <= retained:
            raise ValueError("retained support must be positive")
        self.n_qubits = n_qubits
        self.retained = retained
        self.indices = np.array([0], dtype=np.int64)
        self.amplitudes = np.array([1.0 + 0.0j], dtype=np.complex128)
        self.discarded_probability = 0.0
        self.steps = 0

    def _truncate(self) -> None:
        weights = np.abs(self.amplitudes) ** 2
        total = float(weights.sum())
        if len(weights) > self.retained:
            selected = np.argpartition(weights, -self.retained)[-self.retained :]
            kept_weight = float(weights[selected].sum())
            self.discarded_probability += max(0.0, total - kept_weight)
            selected = selected[np.argsort(self.indices[selected])]
            self.indices = self.indices[selected]
            self.amplitudes = self.amplitudes[selected]
            weights = np.abs(self.amplitudes) ** 2
            total = float(weights.sum())
        if total > 0.0:
            self.amplitudes /= np.sqrt(total)

    def _apply_one(self, event: Event) -> None:
        wire = event.wires[0]
        mask = np.int64(1 << wire)
        indices = self.indices
        low = indices[(indices & mask) == 0]
        high = indices[(indices & mask) != 0] ^ mask
        base = np.unique(np.concatenate((low, high)))
        low_pos = np.searchsorted(indices, base)
        high_pos = np.searchsorted(indices, base ^ mask)
        low_amp = np.zeros(len(base), dtype=np.complex128)
        high_amp = np.zeros(len(base), dtype=np.complex128)
        low_found = (low_pos < len(indices)) & (indices[np.minimum(low_pos, len(indices) - 1)] == base)
        high_indices = base ^ mask
        high_found = (high_pos < len(indices)) & (indices[np.minimum(high_pos, len(indices) - 1)] == high_indices)
        low_amp[low_found] = self.amplitudes[low_pos[low_found]]
        high_amp[high_found] = self.amplitudes[high_pos[high_found]]
        matrix = gate_matrix(event)
        out_low = matrix[0, 0] * low_amp + matrix[0, 1] * high_amp
        out_high = matrix[1, 0] * low_amp + matrix[1, 1] * high_amp
        self.indices = np.concatenate((base, base ^ mask))
        self.amplitudes = np.concatenate((out_low, out_high))
        order = np.argsort(self.indices)
        self.indices = self.indices[order]
        self.amplitudes = self.amplitudes[order]

    def _apply_diagonal(self, event: Event) -> None:
        if event.gate == "cz":
            mask = (1 << event.wires[0]) | (1 << event.wires[1])
            both = (self.indices & mask) == mask
            self.amplitudes[both] *= -1.0
        elif event.gate == "rzz":
            first, second = event.wires
            z_first = 1 - 2 * ((self.indices >> first) & 1)
            z_second = 1 - 2 * ((self.indices >> second) & 1)
            self.amplitudes *= np.exp(-0.5j * event.params[0] * z_first * z_second)
        else:
            raise ValueError(f"unsupported diagonal gate {event.gate}")

    def apply(self, event: Event) -> None:
        if event.gate == "u":
            self._apply_one(event)
            self._truncate()
        elif event.gate in {"cz", "rzz"}:
            self._apply_diagonal(event)
        else:
            raise ValueError(f"unsupported sparse gate {event.gate}")
        self.steps += 1

    def run(self, circuit: CircuitEvents, *, max_seconds: float | None = None) -> SparseRun:
        started = time.perf_counter()
        timed_out = False
        for event in circuit.events:
            if max_seconds is not None and time.perf_counter() - started >= max_seconds:
                timed_out = True
                break
            self.apply(event)
        elapsed = time.perf_counter() - started
        return SparseRun(
            retained_probability=float(np.sum(np.abs(self.amplitudes) ** 2)),
            discarded_probability=self.discarded_probability,
            steps=self.steps,
            elapsed_s=elapsed,
            timed_out=timed_out,
        )

    def probability(self, index: int) -> float:
        position = np.searchsorted(self.indices, index)
        if position >= len(self.indices) or self.indices[position] != index:
            return 0.0
        return float(abs(self.amplitudes[position]) ** 2)
