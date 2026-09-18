from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping

import numpy as np

from .counts_io import validate_counts
from .models import BootstrapReport, RecoveryCandidate

RecoveryFunction = Callable[[Mapping[str, int]], RecoveryCandidate]


def bootstrap_recovery(
    counts: Mapping[str, int],
    method: RecoveryFunction,
    *,
    replicates: int = 1000,
    seed: int = 12345,
    include_candidates: bool = False,
    stable_threshold: float = 0.95,
) -> BootstrapReport:
    if replicates <= 0:
        raise ValueError("replicates must be positive")
    strings = sorted(counts)
    number = len(strings[0]) if strings else 0
    shots = validate_counts(counts, number)
    weights = np.array([counts[s] for s in strings], dtype=float)
    probabilities = weights / shots
    rng = np.random.default_rng(seed)
    full = method(counts)
    candidate_list: list[str] = []
    for _ in range(replicates):
        sampled = rng.multinomial(shots, probabilities)
        resampled = {s: int(c) for s, c in zip(strings, sampled, strict=True) if c}
        candidate_list.append(method(resampled).canonical_bitstring)
    bits = np.array([[ch == "1" for ch in candidate] for candidate in candidate_list], dtype=float)
    per_bit = bits.mean(axis=0)
    stable_mask = np.maximum(per_bit, 1 - per_bit) >= stable_threshold
    modal_counts = Counter(candidate_list)
    modal = min(modal_counts, key=lambda value: (-modal_counts[value], value))
    distances = [
        sum(a != b for a, b in zip(candidate, full.canonical_bitstring, strict=True))
        for candidate in candidate_list
    ]
    intervals = [
        (float(np.quantile(bits[:, i], 0.025)), float(np.quantile(bits[:, i], 0.975)))
        for i in range(number)
    ]
    unstable = np.flatnonzero(~stable_mask).tolist()
    return BootstrapReport(
        method_name=full.method_name,
        replicates=replicates,
        modal_candidate=modal,
        modal_candidate_frequency=modal_counts[modal] / replicates,
        per_bit_selection_probability=per_bit.tolist(),
        hamming_distance_distribution=distances,
        stable_bits=int(stable_mask.sum()),
        unstable_bits=len(unstable),
        unstable_bit_indices=unstable,
        exact_match_stability=candidate_list.count(full.canonical_bitstring) / replicates,
        per_bit_one_probability_intervals_95=intervals,
        replicate_candidates=candidate_list if include_candidates else None,
        random_seed=seed,
    )


def resampled_shot_scaling(
    counts: Mapping[str, int],
    method: RecoveryFunction,
    shot_counts: list[int],
    *,
    repeats: int = 100,
    seed: int = 12345,
) -> list[dict[str, object]]:
    strings = sorted(counts)
    total = validate_counts(counts, len(strings[0]))
    probabilities = np.array([counts[s] for s in strings], dtype=float) / total
    rng = np.random.default_rng(seed)
    result = []
    for shots in shot_counts:
        candidates = []
        for _ in range(repeats):
            sampled = rng.multinomial(shots, probabilities)
            candidates.append(
                method(
                    {s: int(c) for s, c in zip(strings, sampled, strict=True) if c}
                ).canonical_bitstring
            )
        mode, frequency = min(Counter(candidates).items(), key=lambda item: (-item[1], item[0]))
        result.append(
            {
                "analysis_type": "resampled_shot_scaling",
                "shots": shots,
                "repeats": repeats,
                "modal_candidate": mode,
                "modal_candidate_frequency": frequency / repeats,
            }
        )
    return result


def prefix_shot_scaling(
    shots: list[str], method: RecoveryFunction, shot_counts: list[int]
) -> list[dict[str, object]]:
    result = []
    for size in sorted({x for x in shot_counts if 0 < x <= len(shots)}):
        counts = Counter(shots[:size])
        result.append(
            {
                "analysis_type": "empirical_prefix",
                "shots": size,
                "candidate": method(counts).canonical_bitstring,
            }
        )
    return result
