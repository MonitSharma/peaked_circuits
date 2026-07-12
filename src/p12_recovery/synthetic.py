from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import numpy as np


def random_target(number_of_qubits: int = 98, *, seed: int = 12345) -> str:
    rng = np.random.default_rng(seed)
    return "".join(rng.choice(["0", "1"], size=number_of_qubits).tolist())


def _array(target: str) -> np.ndarray:
    if not target or set(target) - {"0", "1"}:
        raise ValueError("Target must be a nonempty canonical binary string")
    return np.fromiter((ch == "1" for ch in target), dtype=np.uint8)


def _strings(samples: np.ndarray) -> list[str]:
    return ["".join(row.astype(str).tolist()) for row in samples]


def independent_bit_flip_shots(
    target: str, shots: int, *, error_probability: float | Sequence[float], seed: int
) -> list[str]:
    target_bits = _array(target)
    probabilities = np.asarray(error_probability, dtype=float)
    if probabilities.ndim == 0:
        probabilities = np.full(len(target), float(probabilities))
    if probabilities.shape != (len(target),) or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Error probabilities must be in [0, 1] and match target width")
    rng = np.random.default_rng(seed)
    flips = rng.random((shots, len(target))) < probabilities
    return _strings(np.bitwise_xor(target_bits, flips))


def asymmetric_readout_shots(
    target: str, shots: int, *, p_1_to_0: float, p_0_to_1: float, seed: int
) -> list[str]:
    bits = _array(target)
    probabilities = np.where(bits == 1, p_1_to_0, p_0_to_1)
    return independent_bit_flip_shots(
        target, shots, error_probability=probabilities.tolist(), seed=seed
    )


def correlated_burst_shots(
    target: str, shots: int, *, groups: Sequence[Sequence[int]], burst_probability: float, seed: int
) -> list[str]:
    if not 0 <= burst_probability <= 1:
        raise ValueError("burst_probability must be in [0, 1]")
    target_bits = _array(target)
    samples = np.tile(target_bits, (shots, 1))
    rng = np.random.default_rng(seed)
    for group in groups:
        indices = np.asarray(group, dtype=int)
        if np.any((indices < 0) | (indices >= len(target))) or len(set(indices.tolist())) != len(
            indices
        ):
            raise ValueError("Burst groups contain invalid or duplicate indices")
        selected = rng.random(shots) < burst_probability
        samples[np.ix_(selected, indices)] ^= 1
    return _strings(samples)


def mixture_shots(
    target: str,
    shots: int,
    *,
    target_weight: float,
    secondary_weight: float,
    uniform_weight: float,
    seed: int,
    secondary_targets: Sequence[str] | None = None,
    cluster_error_probability: float = 0.03,
) -> list[str]:
    weights = np.array([target_weight, secondary_weight, uniform_weight], dtype=float)
    if np.any(weights < 0) or not np.isclose(weights.sum(), 1):
        raise ValueError("Mixture weights must be nonnegative and sum to one")
    secondaries = list(secondary_targets or [target[::-1]])
    if any(len(item) != len(target) or set(item) - {"0", "1"} for item in secondaries):
        raise ValueError("Secondary targets must be canonical and match target width")
    rng = np.random.default_rng(seed)
    labels = rng.choice(3, size=shots, p=weights)
    result: list[str] = []
    for index, label in enumerate(labels):
        child_seed = int(rng.integers(0, np.iinfo(np.int32).max))
        if label == 0:
            result.extend(
                independent_bit_flip_shots(
                    target, 1, error_probability=cluster_error_probability, seed=child_seed
                )
            )
        elif label == 1:
            secondary = secondaries[index % len(secondaries)]
            result.extend(
                independent_bit_flip_shots(
                    secondary, 1, error_probability=cluster_error_probability, seed=child_seed
                )
            )
        else:
            result.append("".join(rng.choice(["0", "1"], size=len(target)).tolist()))
    return result


def aggregate_shots(shots: Sequence[str]) -> dict[str, int]:
    if not shots:
        raise ValueError("Cannot aggregate empty shots")
    return dict(Counter(shots))
