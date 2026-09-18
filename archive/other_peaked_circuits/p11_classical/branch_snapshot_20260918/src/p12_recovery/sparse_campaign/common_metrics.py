"""Answer-free metrics shared by sparse campaign runners."""

from __future__ import annotations

import hashlib
import json
import resource
import sys
from pathlib import Path

import numpy as np


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def bitstring(index: int, n_qubits: int) -> str:
    return f"{int(index):0{n_qubits}b}"


def hamming(left: str, right: str) -> int:
    if len(left) != len(right):
        raise ValueError("bitstrings must have equal length")
    return sum(a != b for a, b in zip(left, right))


def state_support(state) -> tuple[np.ndarray, np.ndarray]:
    return state.x[: state.nnz].copy(), state.alpha[: state.nnz].copy()


def sparse_target_metrics(state, n_qubits: int, target: str) -> dict:
    target_index = int(target, 2)
    indices, amplitudes = state_support(state)
    positions = np.flatnonzero(indices == target_index)
    target_weight = float(abs(amplitudes[positions[0]]) ** 2) if len(positions) else 0.0
    order = np.argsort(np.abs(amplitudes) ** 2)[::-1]
    rank = int(np.flatnonzero(indices[order] == target_index)[0] + 1) if len(positions) else None
    top_index = int(indices[order[0]]) if len(order) else 0
    return {
        "top1_bitstring": bitstring(top_index, n_qubits),
        "top1_hamming_to_p9": hamming(bitstring(top_index, n_qubits), target),
        "target_present": bool(len(positions)),
        "target_rank": rank,
        "target_weight": target_weight,
        "final_nnz": int(state.nnz),
        "norm_squared": float(np.sum(np.abs(amplitudes) ** 2)),
    }


def target_probability_in_product_frame(state, transforms, n_qubits: int, target: str) -> float:
    """Evaluate one computational-basis amplitude from a BASS product frame.

    If ``|psi_Z> = (⊗_j U_j) |psi_frame>``, this contracts only the requested
    computational-basis amplitude and never expands the full Z-basis state.
    """
    target_index = int(target, 2)
    amplitude = 0.0 + 0.0j
    for basis, coefficient in zip(state.x[: state.nnz], state.alpha[: state.nnz]):
        factor = complex(coefficient)
        value = int(basis)
        for qubit, transform in enumerate(transforms):
            target_bit = (target_index >> (n_qubits - 1 - qubit)) & 1
            frame_bit = (value >> qubit) & 1
            factor *= transform[target_bit, frame_bit]
        amplitude += factor
    return float(abs(amplitude) ** 2)


def participation_ratio(amplitudes) -> float:
    probabilities = np.abs(np.asarray(amplitudes)) ** 2
    denominator = float(np.sum(probabilities**2))
    return float(1.0 / denominator) if denominator > 0 else float("inf")


def artifact_hashes(directory: str | Path) -> dict[str, str]:
    directory = Path(directory)
    output = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            output[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return output


def write_json(path: str | Path, payload) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
