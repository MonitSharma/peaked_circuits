"""Small deterministic planted-peak controls for decoder calibration."""

from __future__ import annotations

import numpy as np


def planted_state(n: int, *, peak_probability: float = 0.1, seed: int = 0) -> tuple[np.ndarray, str]:
    if not 0 < peak_probability < 1:
        raise ValueError("peak_probability must lie in (0, 1)")
    rng = np.random.default_rng(seed)
    peak = "".join(str(x) for x in rng.integers(0, 2, n))
    state = rng.normal(size=2**n) + 1j * rng.normal(size=2**n)
    index = int(peak, 2)
    state[index] = 0
    state *= np.sqrt(1 - peak_probability) / np.linalg.norm(state)
    state[index] = np.sqrt(peak_probability)
    return state, peak


def statevector_to_mps(state: np.ndarray, n: int) -> list[np.ndarray]:
    """Factor a small exact statevector into open-boundary MPS tensors."""
    work = np.asarray(state, dtype=np.complex128).reshape(1, *([2] * n))
    tensors = []
    left = 1
    for _ in range(n - 1):
        work = work.reshape(left * 2, -1)
        u, singular, vh = np.linalg.svd(work, full_matrices=False)
        bond = len(singular)
        tensors.append(u.reshape(left, 2, bond))
        work = singular[:, None] * vh
        left = bond
    tensors.append(work.reshape(left, 2, 1))
    return tensors


def control_family(name: str, *, n: int = 20, seed: int = 0) -> dict[str, object]:
    """Return answer-blind metadata; structural labels are not answer data."""
    labels = {"P8": "sparse_planar_iswap", "P6": "weighted_backbone_cz", "P5": "dense_cz_generic_u"}
    if name not in labels:
        raise ValueError(name)
    state, peak = planted_state(n, seed=seed)
    order = np.argsort(-np.abs(state) ** 2)[:2]
    return {"family": labels[name], "n_qubits": n, "seed": seed, "statevector": state, "exact_top1": format(int(order[0]), f"0{n}b"), "exact_top2": format(int(order[1]), f"0{n}b"), "peak_probability": float(np.abs(state[int(peak, 2)]) ** 2), "planted_label_for_test_only": peak}
