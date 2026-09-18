"""Dense local-unitary comparison for only small (2-4 qubit) patches."""

from __future__ import annotations

import math

import numpy as np

from .qasm_events import Event


def gate_matrix(event: Event) -> np.ndarray:
    if event.gate == "u":
        theta, phi, lam = event.params
        c, s = math.cos(theta / 2), math.sin(theta / 2)
        return np.array(
            [[c, -np.exp(1j * lam) * s], [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]],
            dtype=np.complex128,
        )
    if event.gate in {"h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx"}:
        matrices = {
            "h": np.array([[1, 1], [1, -1]]) / np.sqrt(2),
            "x": np.array([[0, 1], [1, 0]]),
            "y": np.array([[0, -1j], [1j, 0]]),
            "z": np.diag([1, -1]),
            "s": np.diag([1, 1j]),
            "sdg": np.diag([1, -1j]),
            "t": np.diag([1, np.exp(1j * np.pi / 4)]),
            "tdg": np.diag([1, np.exp(-1j * np.pi / 4)]),
            "sx": np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]]) / 2,
        }
        return np.asarray(matrices[event.gate], dtype=np.complex128)
    if event.gate == "cz":
        return np.diag([1, 1, 1, -1]).astype(np.complex128)
    if event.gate == "iswap":
        return np.array(
            [[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]],
            dtype=np.complex128,
        )
    if event.gate == "rzz":
        theta = event.params[0] / 2
        return np.diag(
            [np.exp(-1j * theta), np.exp(1j * theta), np.exp(1j * theta), np.exp(-1j * theta)]
        )
    raise ValueError(f"unsupported gate {event.gate}")


def _apply_gate(
    state: np.ndarray,
    matrix: np.ndarray,
    local_wires: tuple[int, ...],
    global_wires: tuple[int, ...],
) -> np.ndarray:
    n = len(global_wires)
    tensor = state.reshape((2,) * n)
    order = list(local_wires) + [index for index in range(n) if index not in local_wires]
    inverse = np.argsort(order)
    moved = np.transpose(tensor, order).reshape(matrix.shape[0], -1)
    moved = matrix @ moved
    return np.transpose(moved.reshape((2,) * n), inverse).reshape(-1)


def patch_unitary(events: tuple[Event, ...] | list[Event], wires: tuple[int, ...]) -> np.ndarray:
    wires = tuple(wires)
    if not 1 <= len(wires) <= 4:
        raise ValueError("patches are limited to one through four qubits")
    unitary = np.eye(2 ** len(wires), dtype=np.complex128)
    for event in events:
        if not set(event.wires).issubset(wires):
            raise ValueError("patch event touches a wire outside the patch")
        local = tuple(wires.index(wire) for wire in event.wires)
        unitary = np.column_stack(
            [
                _apply_gate(unitary[:, column], gate_matrix(event), local, wires)
                for column in range(unitary.shape[1])
            ]
        )
    return unitary


def phase_insensitive_fidelity(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape or left.shape[0] != left.shape[1]:
        raise ValueError("patch matrices must have equal square shape")
    return float(abs(np.trace(left.conj().T @ right)) / left.shape[0])
