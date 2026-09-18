"""Extract two-wire local blocks and calculate Weyl/KAK signatures for P6."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from qiskit.synthesis import TwoQubitWeylDecomposition

from structural.patch_unitary import gate_matrix
from structural.qasm_events import CircuitEvents, Event, parse_qasm


@dataclass(frozen=True)
class Block:
    start_event: int
    end_event: int
    pair: tuple[int, int]
    n_events: int
    n_entanglers: int
    weyl: tuple[float, float, float]
    operator_schmidt: tuple[float, ...]


def _apply(matrix: np.ndarray, gate: np.ndarray, wires: tuple[int, ...]) -> np.ndarray:
    # Qubit order is (pair[0], pair[1]); reshape preserves the conventional
    # computational basis ordering used by Qiskit and patch_unitary.
    result = np.empty_like(matrix)
    for column in range(matrix.shape[1]):
        vector = matrix[:, column].reshape(2, 2)
        if len(wires) == 1:
            axis = wires[0]
            vector = np.tensordot(gate, vector, axes=(1, axis))
            vector = np.moveaxis(vector, 0, axis)
        else:
            vector = gate @ vector.reshape(4)
        result[:, column] = vector.reshape(4)
    return result


def _operator_schmidt(unitary: np.ndarray) -> tuple[float, ...]:
    reshaped = unitary.reshape(2, 2, 2, 2).transpose(0, 2, 1, 3).reshape(4, 4)
    values = np.linalg.svd(reshaped, compute_uv=False)
    return tuple(float(value) for value in values)


def _block_signature(unitary: np.ndarray) -> tuple[tuple[float, float, float], tuple[float, ...]]:
    decomposition = TwoQubitWeylDecomposition(unitary)
    weyl = tuple(float(value) for value in (decomposition.a, decomposition.b, decomposition.c))
    return weyl, _operator_schmidt(unitary)


def extract_blocks(circuit: CircuitEvents) -> list[Block]:
    blocks: list[Block] = []
    events = circuit.events
    for left in range(circuit.n_qubits):
        for right in range(left + 1, circuit.n_qubits):
            pair = (left, right)
            start = None
            local_events: list[Event] = []
            entanglers = 0
            for event in events + (None,):
                is_pair_local = event is not None and set(event.wires).issubset(pair)
                if is_pair_local:
                    if start is None:
                        start = event.index
                    local_events.append(event)
                    entanglers += len(event.wires) == 2
                    continue
                if start is not None and entanglers:
                    unitary = np.eye(4, dtype=np.complex128)
                    for local_event in local_events:
                        wires = tuple(pair.index(wire) for wire in local_event.wires)
                        unitary = _apply(unitary, gate_matrix(local_event), wires)
                    weyl, schmidt = _block_signature(unitary)
                    blocks.append(Block(start, local_events[-1].index, pair,
                                       len(local_events), entanglers, weyl, schmidt))
                start = None
                local_events = []
                entanglers = 0
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit = parse_qasm(args.qasm)
    blocks = extract_blocks(circuit)
    report = {
        "qasm": str(args.qasm),
        "n_qubits": circuit.n_qubits,
        "n_events": len(circuit.events),
        "n_two_qubit": circuit.n_two_qubit,
        "n_blocks": len(blocks),
        "blocks_with_repeated_entanglers": sum(block.n_entanglers > 1 for block in blocks),
        "pair_counts": Counter(f"{a},{b}" for block in blocks for a, b in [block.pair]),
        "blocks": [asdict(block) for block in blocks],
    }
    report["pair_counts"] = dict(report["pair_counts"])
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "blocks"}, indent=2))


if __name__ == "__main__":
    main()
