"""Offline, target-blind diagnostics for one or more physical batches."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from math import ceil

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


def leave_one_batch_out(batch_counts: Sequence[dict[str, int]]) -> list[dict[str, int]]:
    batches = list(batch_counts)
    return [merge_batch_counts(batches[:index] + batches[index + 1 :]) for index in range(len(batches))]


def leave_one_out_counts(counts: dict[str, int]) -> list[dict[str, int]]:
    """Compatibility alias for shot-level deletion; campaigns use leave_one_batch_out."""
    return [{key: value - 1 if key == observed else value for key, value in counts.items() if value - (key == observed) > 0} for observed, value in counts.items()]


def hamming_basin(counts: dict[str, int], candidate: str, radius: int = 2) -> dict[str, object]:
    histogram: Counter[int] = Counter()
    for key, value in counts.items():
        histogram[sum(a != b for a, b in zip(key, candidate, strict=True))] += value
    shots = sum(value for distance, value in histogram.items() if distance <= radius)
    return {"radius": radius, "shots": shots, "fraction": shots / sum(counts.values()), "distance_histogram": dict(sorted(histogram.items()))}


def fixed_radius_basins(counts: dict[str, int], candidate: str, maximum_radius: int = 5) -> dict[str, object]:
    return {str(radius): hamming_basin(counts, candidate, radius) for radius in range(maximum_radius + 1)}


def wilson_intervals(counts: dict[str, int], candidate: str, z: float = 1.959963984540054) -> list[dict[str, float]]:
    total = sum(counts.values())
    intervals: list[dict[str, float]] = []
    for index, bit in enumerate(candidate):
        successes = sum(value for key, value in counts.items() if key[index] == bit)
        proportion = successes / total
        denominator = 1 + z * z / total
        center = (proportion + z * z / (2 * total)) / denominator
        half = z * (proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5 / denominator
        intervals.append({"position": index, "candidate_bit": int(bit), "proportion": proportion, "lower_95": max(0.0, center - half), "upper_95": min(1.0, center + half)})
    return [dict(interval) for interval in intervals]


def _sample_counts(counts: dict[str, int], rng: np.random.Generator, size: int | None = None) -> dict[str, int]:
    keys = sorted(counts)
    observations = np.repeat(np.array(keys), [counts[key] for key in keys])
    return dict(Counter(rng.choice(observations, size=size or len(observations), replace=True)))


def stratified_bootstrap(batch_counts: Sequence[dict[str, int]] | dict[str, int], *, replicates: int = 200, seed: int = 12) -> dict[str, object]:
    batches = [batch_counts] if isinstance(batch_counts, dict) else list(batch_counts)
    rng = np.random.default_rng(seed)
    candidates = [bitwise_majority_string(merge_batch_counts([_sample_counts(batch, rng) for batch in batches])).canonical_bitstring for _ in range(replicates)]
    frequencies = Counter(candidates)
    return {"replicates": replicates, "seed": seed, "candidate": "bitwise_majority", "candidate_frequencies": dict(sorted(frequencies.items())), "modal_candidate": min(frequencies, key=lambda key: (-frequencies[key], key))}


def prefix_convergence(counts: dict[str, int], *, fractions: Sequence[float] = (0.0625, 0.125, 0.1875, 0.25, 0.5, 0.75, 1.0)) -> list[dict[str, object]]:
    observations = np.repeat(np.array(sorted(counts)), [counts[key] for key in sorted(counts)])
    final = bitwise_majority_string(counts).canonical_bitstring
    rows: list[dict[str, object]] = []
    for fraction in fractions:
        size = max(1, min(len(observations), ceil(len(observations) * fraction)))
        candidate = bitwise_majority_string(dict(Counter(observations[:size]))).canonical_bitstring
        rows.append({"shots": size, "candidate": candidate, "hamming_to_final": sum(a != b for a, b in zip(candidate, final, strict=True))})
    return rows


def random_subsample_convergence(counts: dict[str, int], *, sizes: Sequence[int] = (50, 100, 150, 200, 250, 300, 350), replicates: int = 100, seed: int = 12) -> list[dict[str, object]]:
    observations = np.repeat(np.array(sorted(counts)), [counts[key] for key in sorted(counts)])
    final = bitwise_majority_string(counts).canonical_bitstring
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for size in sizes:
        if size > len(observations):
            continue
        matches = 0
        for _ in range(replicates):
            candidate = bitwise_majority_string(dict(Counter(rng.choice(observations, size=size, replace=False)))).canonical_bitstring
            matches += candidate == final
        rows.append({"shots": size, "replicates": replicates, "match_probability": matches / replicates})
    return rows


def analyze_batch(counts: dict[str, int], *, seed: int = 12) -> dict[str, object]:
    methods = [most_frequent_string(counts), bitwise_majority_string(counts), weighted_observed_medoid(counts), cluster_consensus(counts)]
    candidates = {item.method_name: item.canonical_bitstring for item in methods}
    primary = candidates["bitwise_majority"]
    return {"shots": sum(counts.values()), "unique_strings": len(counts), "candidates": candidates, "agreement": method_agreement(methods), "primary_candidate": primary, "primary_candidate_observed_count": counts.get(primary, 0), "wilson_intervals_95": wilson_intervals(counts, primary), "basins": fixed_radius_basins(counts, primary), "prefix_convergence": prefix_convergence(counts), "random_subsample_convergence": random_subsample_convergence(counts, seed=seed), "bootstrap": stratified_bootstrap(counts, seed=seed)}


def analyze_batches(batch_counts: Sequence[dict[str, int]], *, seed: int = 12) -> dict[str, object]:
    pooled = merge_batch_counts(batch_counts)
    return {"batch_count": len(batch_counts), "per_batch": [analyze_batch(counts, seed=seed + index) for index, counts in enumerate(batch_counts)], "cumulative": analyze_batch(pooled, seed=seed), "leave_one_batch_out": [analyze_batch(counts, seed=seed + index) for index, counts in enumerate(leave_one_batch_out(batch_counts))], "stratified_bootstrap": stratified_bootstrap(batch_counts, seed=seed)}
