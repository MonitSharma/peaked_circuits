"""Sparse computational-basis simulation specialized for U + CZ P1 circuits."""

from __future__ import annotations

import hashlib
import json
import os
try:
    import resource
except ImportError:  # pragma: no cover - Windows has no stdlib resource module.
    resource = None
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from structural.qasm_events import Event, parse_qasm
from .profile import _u_matrix


@dataclass
class SparseState:
    n_qubits: int
    dtype: np.dtype = np.dtype(np.complex128)
    basis: np.ndarray = field(default_factory=lambda: np.array([0], dtype=np.int64))
    alpha: np.ndarray = field(default_factory=lambda: np.array([1.0 + 0.0j], dtype=np.complex128))

    def __post_init__(self) -> None:
        self.basis = np.asarray(self.basis, dtype=np.int64)
        self.alpha = np.asarray(self.alpha, dtype=self.dtype)

    @property
    def support(self) -> int:
        return int(self.basis.size)

    @property
    def norm(self) -> float:
        return float(np.sum(np.abs(self.alpha) ** 2))

    def evolve_cz(self, q0: int, q1: int) -> None:
        """Apply diagonal CZ in place without changing computational support."""
        mask = ((self.basis >> np.int64(q0)) & 1) & ((self.basis >> np.int64(q1)) & 1)
        self.alpha[mask.astype(bool)] *= -1

    def evolve_iswap(self, q0: int, q1: int) -> None:
        """Apply iSWAP in place; it permutes support and adds phases only."""
        if q0 == q1:
            raise ValueError("iSWAP requires two distinct qubits")
        bit0 = np.int64(1) << np.int64(q0)
        bit1 = np.int64(1) << np.int64(q1)
        differing = (((self.basis >> np.int64(q0)) ^ (self.basis >> np.int64(q1))) & 1).astype(bool)
        self.basis[differing] ^= bit0 | bit1
        self.alpha[differing] *= 1j

    def evolve_u(self, matrix: np.ndarray, q: int) -> None:
        """Apply a one-qubit U with at most two output indices per input."""
        bit = np.int64(1) << np.int64(q)
        selected = ((self.basis >> np.int64(q)) & 1).astype(np.int64)
        other = self.basis & ~bit
        b0, b1 = other, other | bit
        a0 = matrix[0, 0] * self.alpha * (selected == 0) + matrix[0, 1] * self.alpha * (selected == 1)
        a1 = matrix[1, 0] * self.alpha * (selected == 0) + matrix[1, 1] * self.alpha * (selected == 1)
        out_basis = np.concatenate((b0, b1))
        out_alpha = np.concatenate((a0, a1))
        basis, inverse = np.unique(out_basis, return_inverse=True)
        alpha = np.zeros(basis.size, dtype=self.dtype)
        np.add.at(alpha, inverse, out_alpha)
        keep = np.abs(alpha) > 0
        self.basis, self.alpha = basis[keep], alpha[keep]

    def evolve_local(self, matrix: np.ndarray, qargs: list[int]) -> None:
        """Apply a small dense local matrix to the retained sparse support."""
        qargs = list(qargs)
        width = len(qargs)
        qrange = np.arange(width, dtype=np.int64)
        cols = np.sum((((self.basis[:, None] >> np.asarray(qargs)) & 1) << qrange), axis=1)
        amplitudes = matrix[:, cols] * self.alpha[None, :]
        local_bits = np.arange(1 << width, dtype=np.int64)
        output_offsets = np.zeros(1 << width, dtype=np.int64)
        for local_index, bits in enumerate(local_bits):
            for position, q in enumerate(qargs):
                if (bits >> position) & 1:
                    output_offsets[local_index] |= np.int64(1) << np.int64(q)
        cleared = self.basis.copy()
        for q in qargs:
            cleared &= ~(np.int64(1) << np.int64(q))
        out_basis = (cleared[None, :] | output_offsets[:, None]).ravel()
        out_alpha = amplitudes.ravel()
        basis, inverse = np.unique(out_basis, return_inverse=True)
        alpha = np.zeros(basis.size, dtype=self.dtype)
        np.add.at(alpha, inverse, out_alpha)
        keep = np.abs(alpha) > 0
        self.basis, self.alpha = basis[keep], alpha[keep]

    def truncate(self, top_k: int, p_frac: float = 1.0) -> dict[str, float | int | bool]:
        if not 0.0 < p_frac <= 1.0:
            raise ValueError("p_frac must be in (0, 1]")
        if top_k <= 0 and p_frac >= 1.0:
            return {"support_before": self.support, "support_after": self.support, "discarded_mass": 0.0, "renormalized": False}
        probs = np.abs(self.alpha) ** 2
        order = np.argsort(probs)[::-1]
        keep_count = self.support if p_frac >= 1.0 else int(np.searchsorted(np.cumsum(probs[order]) / np.sum(probs), p_frac) + 1)
        if top_k > 0:
            keep_count = min(keep_count, top_k)
        keep = order[:keep_count]
        retained = float(np.sum(probs[keep]))
        discarded = float(max(0.0, np.sum(probs) - retained))
        self.basis, self.alpha = self.basis[keep], self.alpha[keep]
        if retained > 0:
            self.alpha /= np.sqrt(retained)
        return {"support_before": int(probs.size), "support_after": self.support, "discarded_mass": discarded, "renormalized": True}

    def top(self, count: int = 32) -> list[dict[str, float | str]]:
        if not self.support:
            return []
        probs = np.abs(self.alpha) ** 2
        order = np.argsort(probs)[::-1][:count]
        return [{"bitstring": f"{int(self.basis[i]):0{self.n_qubits}b}", "probability_renormalized": float(probs[i])} for i in order]


def _rss_bytes() -> int:
    if resource is None:
        return 0
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Darwin reports bytes; Linux reports KiB.
    return int(value if os.uname().sysname == "Darwin" else value * 1024)


def dependency_schedule(events: tuple[Event, ...], policy: str = "original") -> list[Event]:
    """Return a legal topological schedule using only same-wire dependencies."""
    if policy == "original":
        return list(events)
    if policy != "cz_first":
        raise ValueError(f"unknown sparse schedule: {policy}")
    predecessors: dict[int, int] = {}
    successors: dict[int, list[int]] = {event.index: [] for event in events}
    indegree: dict[int, int] = {event.index: 0 for event in events}
    for event in events:
        deps = {predecessors[q] for q in event.wires if q in predecessors}
        indegree[event.index] = len(deps)
        for dep in deps:
            successors[dep].append(event.index)
        for q in event.wires:
            predecessors[q] = event.index
    by_index = {event.index: event for event in events}
    ready = [event.index for event in events if indegree[event.index] == 0]
    ordered: list[Event] = []
    while ready:
        ready.sort(key=lambda index: (by_index[index].gate not in {"cz", "iswap"}, index))
        index = ready.pop(0)
        ordered.append(by_index[index])
        for successor in successors[index]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    if len(ordered) != len(events):
        raise RuntimeError("dependency graph contains a cycle")
    return ordered


def run_sparse_circuit(
    qasm_path: str | Path,
    top_k: int,
    outdir: str | Path,
    *,
    dtype: str = "complex128",
    max_rss_bytes: int = 30 * 1024**3,
    max_seconds: float = 120.0,
    p_frac: float = 1.0,
    schedule: str = "original",
) -> dict:
    """Run one bounded sparse trajectory and persist a resumable result."""
    path, outdir = Path(qasm_path), Path(outdir)
    circuit = parse_qasm(path)
    np_dtype = np.dtype(dtype)
    state = SparseState(circuit.n_qubits, dtype=np_dtype, alpha=np.array([1 + 0j], dtype=np_dtype))
    started = time.monotonic()
    total_discarded = 0.0
    max_support = state.support
    trace: list[dict] = []
    aborted = None
    events = dependency_schedule(circuit.events, schedule)
    for event in events:
        if event.gate == "cz":
            state.evolve_cz(*event.wires)
        elif event.gate == "u":
            state.evolve_u(_u_matrix(*event.params).astype(np_dtype), event.wires[0])
        else:
            raise ValueError(f"P1 sparse adapter only supports U/CZ, got {event.gate}")
        trunc = state.truncate(top_k, p_frac)
        total_discarded += float(trunc["discarded_mass"])
        max_support = max(max_support, state.support)
        rss = _rss_bytes()
        if event.index % 25 == 0 or trunc["renormalized"]:
            trace.append({"gate_index": event.index, "gate": event.gate, "support": state.support, "support_before_truncation": trunc["support_before"], "discarded_mass_before_renormalization": trunc["discarded_mass"], "norm": state.norm, "rss_bytes": rss})
        if rss >= max_rss_bytes:
            aborted = "rss_hard_abort"
            break
        if time.monotonic() - started >= max_seconds:
            aborted = "wall_time_abort"
            break
    result = {
        "schema": "bluequbit-p1-v2-sparse-run-v1",
        "blind": True,
        "qasm_path": str(path),
        "qasm_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "configuration": {"top_k": top_k, "p_frac": p_frac, "dtype": dtype, "schedule": schedule, "max_rss_bytes": max_rss_bytes, "max_seconds": max_seconds},
        "progress": {"events_completed": len(trace) and (len(events) if aborted is None else None), "events_total": len(events), "aborted": aborted},
        "runtime_s": time.monotonic() - started,
        "peak_rss_bytes": _rss_bytes(),
        "max_support": max_support,
        "final_support": state.support,
        "cumulative_discarded_mass_proxy": total_discarded,
        "final_norm": state.norm,
        "top_candidates": state.top(32),
        "trace": trace,
    }
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "run.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
