"""Offline, target-blind analysis helpers for physical P12 batches."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

import numpy as np

from .recovery import (
    bitwise_majority_string,
    cluster_consensus,
    method_agreement,
    most_frequent_string,
    weighted_observed_medoid,
)


def merge_batch_counts(batches: Iterable[dict[str, int]]) -> dict[str, int]:
    merged: Counter[str] = Counter()
    for counts in batches:
        merged.update(counts)
    return dict(sorted(merged.items()))


def leave_one_out_counts(counts: dict[str, int]) -> list[dict[str, int]]:
    return [
        {key: value - 1 if key == observed else value for key, value in counts.items() if value - (key == observed) > 0}
        for observed, value in counts.items()
        for _ in range(min(value, 1))
    ]


def hamming_basin(counts: dict[str, int], candidate: str, radius: int = 2) -> dict[str, object]:
    distances = {key: sum(a != b for a, b in zip(key, candidate, strict=True)) for key in counts}
    return {"radius": radius, "shots": sum(v for key, v in counts.items() if distances[key] <= radius), "fraction": sum(v for key, v in counts.items() if distances[key] <= radius) / sum(counts.values()), "distance_histogram": dict(sorted(Counter({d: sum(v for k, v in counts.items() if distances[k] == d) for d in set(distances.values())}).items()))}


def stratified_bootstrap(counts: dict[str, int], *, replicates: int = 200, seed: int = 12) -> dict[str, object]:
    keys = sorted(counts)
    observations = np.repeat(np.array(keys), [counts[key] for key in keys])
    rng = np.random.default_rng(seed)
    candidates: list[str] = []
    for _ in range(replicates):
        sample = rng.choice(observations, size=len(observations), replace=True)
        candidates.append(most_frequent_string(dict(Counter(sample))).canonical_bitstring)
    frequencies = Counter(candidates)
    return {"replicates": replicates, "seed": seed, "candidate_frequencies": dict(sorted(frequencies.items())), "modal_candidate": min(frequencies, key=lambda key: (-frequencies[key], key))}


def analyze_batch(counts: dict[str, int], *, seed: int = 12) -> dict[str, object]:
    methods = [
        most_frequent_string(counts),
        bitwise_majority_string(counts),
        weighted_observed_medoid(counts),
        cluster_consensus(counts),
    ]
    candidates = {item.method_name: item.canonical_bitstring for item in methods}
    return {"shots": sum(counts.values()), "unique_strings": len(counts), "candidates": candidates, "agreement": method_agreement(methods), "basins": {name: hamming_basin(counts, value) for name, value in candidates.items()}, "bootstrap": stratified_bootstrap(counts, seed=seed)}
