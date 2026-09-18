"""Bounded stochastic sparse-state evolution for U/CZ circuits.

The particle ensemble is a randomized representation of the state vector. After
each non-diagonal gate, expanded terms are merged and resampled with weights
proportional to squared amplitude. The reweighting is unbiased for each
amplitude, but variance can be large; this module therefore reports ensembles,
not certified probabilities.
"""

from __future__ import annotations

import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np

from structural.qasm_events import parse_qasm
from .profile import _u_matrix


def _rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _merge(basis: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    keys, inverse = np.unique(basis, return_inverse=True)
    values = np.zeros(keys.size, dtype=alpha.dtype)
    np.add.at(values, inverse, alpha)
    keep = np.abs(values) > 0
    return keys[keep], values[keep]


def _resample(basis: np.ndarray, alpha: np.ndarray, particles: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    weights = np.abs(alpha) ** 2
    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        raise FloatingPointError("particle weights became non-finite or zero")
    probabilities = weights / total
    selected = rng.choice(len(basis), size=particles, replace=True, p=probabilities)
    basis_out = basis[selected]
    alpha_out = alpha[selected] / (particles * probabilities[selected])
    # Merge duplicates immediately to keep the next expansion bounded.
    return _merge(basis_out, alpha_out)


def run_particle_circuit(qasm_path: str | Path, particles: int, seed: int, out: str | Path, *, max_seconds: float = 120.0) -> dict:
    path = Path(qasm_path)
    circuit = parse_qasm(path)
    rng = np.random.default_rng(seed)
    basis = np.array([0], dtype=np.int64)
    alpha = np.array([1.0 + 0.0j], dtype=np.complex128)
    started = time.monotonic()
    aborted = None
    error = None
    for event in circuit.events:
        try:
            if event.gate == "cz":
                mask = (((basis >> event.wires[0]) & 1) & ((basis >> event.wires[1]) & 1)).astype(bool)
                alpha[mask] *= -1
            elif event.gate == "u":
                matrix = _u_matrix(*event.params)
                bit = np.int64(1) << np.int64(event.wires[0])
                selected = ((basis >> np.int64(event.wires[0])) & 1).astype(np.int64)
                other = basis & ~bit
                out_basis = np.concatenate((other, other | bit))
                out_alpha = np.concatenate((matrix[0, 0] * alpha * (selected == 0) + matrix[0, 1] * alpha * (selected == 1), matrix[1, 0] * alpha * (selected == 0) + matrix[1, 1] * alpha * (selected == 1)))
                basis, alpha = _merge(out_basis, out_alpha)
                if basis.size > particles:
                    basis, alpha = _resample(basis, alpha, particles, rng)
            else:
                raise ValueError(event.gate)
        except FloatingPointError as exc:
            aborted = "numerical_weight_overflow"
            error = str(exc)
            break
        if time.monotonic() - started >= max_seconds:
            aborted = "wall_time_abort"
            break
    basis, alpha = _merge(basis, alpha)
    order = np.argsort(np.abs(alpha) ** 2)[::-1][:32]
    result = {
        "schema": "bluequbit-p1-v2-particle-state-run-v1",
        "blind": True,
        "qasm_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "configuration": {"particles": particles, "seed": seed, "dtype": "complex128", "resampling": "squared_amplitude_unbiased_reweighting", "max_seconds": max_seconds},
        "events_completed": event.index + 1,
        "events_total": len(circuit.events),
        "aborted": aborted,
        "error": error,
        "runtime_s": time.monotonic() - started,
        "peak_rss_bytes": _rss_bytes(),
        "final_support": int(basis.size),
        "top_candidates": [{"bitstring": f"{int(basis[i]):0{circuit.n_qubits}b}", "amplitude_magnitude_squared_estimate": float(abs(alpha[i]) ** 2)} for i in order],
        "decision": "INCONCLUSIVE_UNLESS_REPEATED_ACROSS_SEEDS",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, indent=2) + "\n")
    return result
