"""Actual-MPO finite-horizon schedule evaluation.

The adapter is intentionally solver-agnostic at import time. On HPC,
``P9SolverMPOBackend`` binds to the pinned ``p9solver`` checkout and uses its
real ``apply_swaps`` and ``apply_circuit`` tensor operations. Candidate probes
return new MPO networks; the parent snapshot is never mutated.
"""

from __future__ import annotations

import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence


class MPOBackend(Protocol):
    def apply_swaps(self, mpo: Any, swaps: Sequence[tuple[int, int]], *, max_bond: int, cutoff: float) -> Any: ...
    def apply_work(self, mpo: Any, layer: Any, *, max_bond: int, cutoff: float) -> Any: ...
    def metrics(self, mpo: Any) -> dict[str, float]: ...


@dataclass(frozen=True)
class MPOSnapshot:
    mpo: Any
    permutation: tuple[int, ...]
    useful_gates: int = 0
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateScore:
    swaps: tuple[tuple[int, int], ...]
    useful_gates_drained: int
    tensor_elements: float
    max_bond: float
    routing_debt: float
    truncation: dict[str, float]
    runtime_s: float
    failure: str | None = None
    snapshot: MPOSnapshot | None = None

    @property
    def lexicographic_key(self) -> tuple[float, ...]:
        return (
            float(self.useful_gates_drained),
            -self.tensor_elements,
            -self.max_bond,
            -self.routing_debt,
            -self.runtime_s,
        )


class P9SolverMPOBackend:
    """Bridge to the pinned p9solver's real MPO operations."""

    def __init__(self, *, swap_representation: str = "cx") -> None:
        from p9solver import mpo as mpo_ops
        from p9solver import pipeline

        self._mpo_ops = mpo_ops
        self._pipeline = pipeline
        self._swap_representation = swap_representation

    def apply_swaps(self, mpo, swaps, *, max_bond, cutoff):
        return self._mpo_ops.apply_swaps(
            mpo,
            swaps_l=list(swaps),
            swaps_r=[],
            max_bond=max_bond,
            cutoff=cutoff,
            method="mpo",
            swap_gate_representation=self._swap_representation,
        )

    def apply_work(self, mpo, layer, *, max_bond, cutoff):
        return self._mpo_ops.apply_circuit(
            mpo, layer, side="right", max_bond=max_bond, cutoff=cutoff, contract=True, compress=True
        )

    def metrics(self, mpo) -> dict[str, float]:
        return {
            "tensor_elements": float(self._pipeline.elem_counts(mpo)),
            "max_bond": float(mpo.max_bond()),
        }


class RealMPOBeamEvaluator:
    """Probe/commit interface used by the HPC beam coordinator."""

    def __init__(self, backend: MPOBackend, *, max_bond: int, cutoff: float) -> None:
        self.backend = backend
        self.max_bond = max_bond
        self.cutoff = cutoff

    def snapshot_state(self, mpo: Any, *, permutation: Sequence[int] | None = None, useful_gates: int = 0, provenance: dict[str, Any] | None = None) -> MPOSnapshot:
        return MPOSnapshot(mpo, tuple(permutation or range(len(getattr(mpo, "sites", ())))), useful_gates, provenance or {})

    def evaluate_schedule(
        self,
        snapshot: MPOSnapshot,
        swaps: Sequence[tuple[int, int]],
        *,
        work_layers: Sequence[Any] = (),
        routing_debt: float = 0.0,
    ) -> CandidateScore:
        started = time.perf_counter()
        candidate = snapshot.mpo
        try:
            for swap in swaps:
                candidate = self.backend.apply_swaps(candidate, (swap,), max_bond=self.max_bond, cutoff=self.cutoff)
            drained = 0
            for layer in work_layers:
                candidate = self.backend.apply_work(candidate, layer, max_bond=self.max_bond, cutoff=self.cutoff)
                drained += int(getattr(layer, "num_gates", len(layer) if hasattr(layer, "__len__") else 1))
            metrics = self.backend.metrics(candidate)
            child = MPOSnapshot(candidate, snapshot.permutation, snapshot.useful_gates + drained, snapshot.provenance)
            return CandidateScore(tuple(swaps), drained, metrics["tensor_elements"], metrics["max_bond"], float(routing_debt), {}, time.perf_counter() - started, snapshot=child)
        except Exception as exc:
            return CandidateScore(tuple(swaps), 0, float("inf"), float("inf"), float(routing_debt), {}, time.perf_counter() - started, failure=f"{type(exc).__name__}: {exc}")

    def choose_and_commit(self, snapshot: MPOSnapshot, candidates: Sequence[CandidateScore]) -> tuple[MPOSnapshot, CandidateScore]:
        valid = [candidate for candidate in candidates if candidate.failure is None and candidate.snapshot is not None]
        if not valid:
            raise RuntimeError("all MPO beam candidates failed")
        winner = max(valid, key=lambda candidate: candidate.lexicographic_key)
        return winner.snapshot, winner

    @staticmethod
    def checkpoint(snapshot: MPOSnapshot, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump(snapshot, handle, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def restore(path: str | Path) -> MPOSnapshot:
        with Path(path).open("rb") as handle:
            snapshot = pickle.load(handle)
        if not isinstance(snapshot, MPOSnapshot):
            raise TypeError("checkpoint is not an MPOSnapshot")
        return snapshot
