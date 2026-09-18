"""Bounded numerical arbitrary-1q/fixed-entangler local synthesis fallback."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from structural.patch_unitary import patch_unitary, phase_insensitive_fidelity
from structural.qasm_events import Event


@dataclass(frozen=True)
class NumericalResult:
    qubits: int
    old_two_qubit: int
    new_two_qubit: int
    fidelity: float
    infidelity: float
    pair_schedule: tuple[tuple[int, int], ...]
    restarts: int
    runtime_s: float
    optimizer: str
    success: bool
    reason: str


def _u3(theta: float, phi: float, lam: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array(
        [[c, -np.exp(1j * lam) * s], [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]],
        dtype=np.complex128,
    )


def _apply(state: np.ndarray, matrix: np.ndarray, local_wires: tuple[int, ...], n: int) -> np.ndarray:
    tensor = state.reshape((2,) * n)
    order = list(local_wires) + [i for i in range(n) if i not in local_wires]
    inverse = np.argsort(order)
    moved = np.transpose(tensor, order).reshape(matrix.shape[0], -1)
    moved = matrix @ moved
    return np.transpose(moved.reshape((2,) * n), inverse).reshape(-1)


def _apply_unitary(unitary: np.ndarray, matrix: np.ndarray, wires: tuple[int, ...], n: int) -> np.ndarray:
    return np.column_stack([_apply(unitary[:, i], matrix, wires, n) for i in range(unitary.shape[1])])


def _ansatz(params: np.ndarray, n: int, pairs: tuple[tuple[int, int], ...]) -> np.ndarray:
    out = np.eye(2**n, dtype=np.complex128)
    cursor = 0
    for layer in range(len(pairs) + 1):
        for wire in range(n):
            out = _apply_unitary(out, _u3(*params[cursor : cursor + 3]), (wire,), n)
            cursor += 3
        if layer < len(pairs):
            # CZ is fixed and has the same entangling cost as any nontrivial 2q update.
            out = _apply_unitary(out, np.diag([1, 1, 1, -1]).astype(np.complex128), pairs[layer], n)
    return out


def _residual(params: np.ndarray, target: np.ndarray, n: int, pairs: tuple[tuple[int, int], ...]) -> np.ndarray:
    candidate = _ansatz(params, n, pairs)
    phase = np.trace(target.conj().T @ candidate)
    if abs(phase) > 0:
        candidate *= np.exp(-1j * np.angle(phase))
    delta = candidate - target
    return np.concatenate((delta.real.ravel(), delta.imag.ravel()))


def synthesize_numerical(
    events: tuple[Event, ...],
    wires: tuple[int, ...],
    old_two_qubit: int,
    pair_candidates: tuple[tuple[int, int], ...],
    *,
    restarts: int,
    seed: int,
    max_nfev: int = 180,
    tolerance: float = 1e-10,
    wall_clock_s: float = 20.0,
    target_matrix: np.ndarray | None = None,
) -> NumericalResult:
    """Try old_2q-1 entanglers, with deterministic bounded restarts."""
    n = len(wires)
    target = patch_unitary(events, wires) if target_matrix is None else np.asarray(target_matrix, dtype=np.complex128)
    local_pairs = tuple((wires.index(a), wires.index(b)) for a, b in pair_candidates)
    if old_two_qubit <= 1 or not local_pairs:
        return NumericalResult(n, old_two_qubit, old_two_qubit, 0.0, 1.0, (), 0, 0.0, "scipy.least_squares", False, "no strict lower entangler target")
    start_time = time.monotonic()
    rng = np.random.default_rng(seed)
    best_fidelity = 0.0
    best_pairs: tuple[tuple[int, int], ...] = ()
    attempts = 0
    target_entanglers = old_two_qubit - 1
    # Try every distinct local pair for the one-entangler case; for larger targets
    # use the original interaction order, truncated to the required count.
    schedules = []
    for pair in dict.fromkeys(local_pairs):
        schedules.append((pair,) if target_entanglers == 1 else tuple(local_pairs[:target_entanglers]))
    for schedule in dict.fromkeys(schedules):
        if time.monotonic() - start_time >= wall_clock_s:
            break
        nparams = 3 * n * (len(schedule) + 1)
        for _ in range(restarts):
            if time.monotonic() - start_time >= wall_clock_s:
                break
            attempts += 1
            initial = rng.uniform(-math.pi, math.pi, nparams)
            fit = least_squares(
                _residual, initial, args=(target, n, schedule), method="trf",
                max_nfev=max_nfev, ftol=1e-10, xtol=1e-10, gtol=1e-10,
            )
            candidate = _ansatz(fit.x, n, schedule)
            fidelity = phase_insensitive_fidelity(target, candidate)
            if fidelity > best_fidelity:
                best_fidelity = fidelity
                best_pairs = schedule
    infidelity = max(0.0, 1.0 - best_fidelity)
    success = best_fidelity >= 1.0 - tolerance and len(best_pairs) < old_two_qubit
    return NumericalResult(
        n, old_two_qubit, len(best_pairs) if best_pairs else old_two_qubit,
        best_fidelity, infidelity, best_pairs, attempts, time.monotonic() - start_time,
        "scipy.least_squares", success,
        "verified strict reduction" if success else "no verified strict reduction within bounded budget",
    )
