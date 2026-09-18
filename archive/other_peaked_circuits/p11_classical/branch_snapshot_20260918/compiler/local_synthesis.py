"""Bounded exact local-block synthesis with a virtual-permutation ledger.

The implementation deliberately keeps the search local: dense matrices are only
formed for blocks on at most four wires.  Optional whole-circuit synthesizers are
not required; Qiskit's exact two-qubit basis decomposer is used when available.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

import numpy as np

from structural.patch_unitary import patch_unitary, phase_insensitive_fidelity
from structural.qasm_events import CircuitEvents, Event


@dataclass(frozen=True)
class LocalBlock:
    start: int
    stop: int
    wires: tuple[int, ...]
    events: tuple[Event, ...]
    old_two_qubit: int


@dataclass(frozen=True)
class SynthesisResult:
    block: LocalBlock
    status: str
    accepted: bool
    old_two_qubit: int
    new_two_qubit: int | None
    fidelity: float | None
    permutation: tuple[int, ...]
    tried_permutations: tuple[tuple[int, ...], ...]
    reason: str


def extract_dependency_blocks(
    circuit: CircuitEvents,
    block_size: int,
    *,
    max_global_span: int = 48,
    max_entanglers: int = 6,
) -> tuple[LocalBlock, ...]:
    """Extract causal patches while ignoring operations on disjoint wires.

    A candidate is bounded by the first/last selected entangling operation. Any
    operation touching a selected wire but extending outside the patch is a
    causal boundary and rejects that candidate. Operations wholly disjoint from
    the patch are omitted and therefore do not falsely split the patch.
    """
    if block_size not in {3, 4}:
        raise ValueError("dependency blocks are intended for 3 or 4 qubits")
    q2 = circuit.two_qubit
    found: dict[tuple[int, int, tuple[int, ...]], LocalBlock] = {}
    for start in range(len(q2)):
        wires: set[int] = set()
        selected: list[Event] = []
        for stop in range(start, min(len(q2), start + max_entanglers)):
            wires |= set(q2[stop].wires)
            if len(wires) > block_size:
                break
            selected.append(q2[stop])
            first = selected[0].index
            last = selected[-1].index
            if last - first > max_global_span:
                break
            patch_wires = tuple(sorted(wires))
            span = circuit.events[first : last + 1]
            if any(set(event.wires) & wires and not set(event.wires).issubset(wires) for event in span):
                continue
            local = tuple(event for event in span if set(event.wires).issubset(wires))
            old = sum(len(event.wires) == 2 for event in local)
            if old < 2:
                continue
            key = (first, last + 1, patch_wires)
            found[key] = LocalBlock(first, last + 1, patch_wires, local, old)
    return tuple(sorted(found.values(), key=lambda block: (block.start, block.stop, block.wires)))


def extract_blocks(
    circuit: CircuitEvents,
    block_size: int,
    *,
    offset: int = 0,
    max_events: int = 12,
) -> tuple[LocalBlock, ...]:
    """Extract disjoint contiguous event blocks with at least two interactions."""
    if block_size not in {2, 3, 4}:
        raise ValueError("block_size must be 2, 3, or 4")
    events = circuit.events
    blocks: list[LocalBlock] = []
    cursor = max(0, offset)
    while cursor < len(events):
        used: set[int] = set()
        end = cursor
        while end < len(events) and end - cursor < max_events:
            candidate = used | set(events[end].wires)
            if len(candidate) > block_size:
                break
            used = candidate
            end += 1
        local = tuple(events[cursor:end])
        two = sum(len(event.wires) == 2 for event in local)
        if two >= 2 and len(used) <= block_size:
            blocks.append(LocalBlock(cursor, end, tuple(sorted(used)), local, two))
            cursor = end
        else:
            cursor += 1
    return tuple(blocks)


def middle_out_order(blocks: tuple[LocalBlock, ...], event_count: int) -> tuple[LocalBlock, ...]:
    """Return blocks ordered by distance from the temporal midpoint."""
    midpoint = event_count / 2
    return tuple(sorted(blocks, key=lambda block: (abs((block.start + block.stop) / 2 - midpoint), block.start)))


def _two_qubit_synthesize(unitary: np.ndarray) -> tuple[object, int]:
    from qiskit.circuit.library import CXGate
    from qiskit.quantum_info import Operator
    from qiskit.synthesis import TwoQubitBasisDecomposer

    decomposer = TwoQubitBasisDecomposer(CXGate())
    circuit = decomposer(Operator(unitary))
    two = sum(item.operation.num_qubits == 2 for item in circuit.data)
    return circuit, two


def synthesize_block(block: LocalBlock) -> SynthesisResult:
    """Attempt exact q=2 synthesis; record bounded permutation candidates for q>2."""
    tried = tuple(permutations(block.wires))
    if len(block.wires) != 2:
        return SynthesisResult(
            block, "unavailable_no_bqskit", False, block.old_two_qubit, None,
            None, tuple(block.wires), tried,
            "qiskit fallback is exact for two wires only; BQSKit unavailable",
        )
    try:
        target = patch_unitary(block.events, block.wires)
        replacement, new_two = _two_qubit_synthesize(target)
        from qiskit.quantum_info import Operator

        fidelity = phase_insensitive_fidelity(target, Operator(replacement).data)
        accepted = bool(new_two < block.old_two_qubit and fidelity >= 1.0 - 1e-10)
        return SynthesisResult(
            block, "verified" if accepted else "verified_no_improvement", accepted,
            block.old_two_qubit, new_two, fidelity, tuple(block.wires), tried,
            "exact operator match" if accepted else "exact replacement does not reduce 2q count",
        )
    except Exception as exc:  # optional dependency/API failure is a branch result
        return SynthesisResult(
            block, "unavailable_qiskit_fallback", False, block.old_two_qubit, None,
            None, tuple(block.wires), tried, f"{type(exc).__name__}: {exc}",
        )
