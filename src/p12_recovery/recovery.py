from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import asdict
from typing import Literal

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

from .counts_io import validate_counts
from .hashing import hash_config
from .models import RecoveryCandidate, TargetScore

TiePolicy = Literal["zero", "one", "uncertain_zero", "uncertain_one"]


def _matrix(counts: Mapping[str, int]) -> tuple[list[str], np.ndarray, np.ndarray]:
    number = len(next(iter(counts))) if counts else 0
    validate_counts(counts, number)
    strings = sorted(counts)
    values = np.fromiter((counts[s] for s in strings), dtype=np.int64)
    bits = np.array([[ch == "1" for ch in s] for s in strings], dtype=np.uint8)
    return strings, values, bits


def _candidate(
    method: str,
    bitstring: str,
    shots: int,
    started: float,
    *,
    parameters: dict[str, object] | None = None,
    confidence: dict[str, object] | None = None,
    warnings: list[str] | None = None,
) -> RecoveryCandidate:
    params = parameters or {}
    return RecoveryCandidate(
        method_name=method,
        canonical_bitstring=bitstring,
        number_of_qubits=len(bitstring),
        parameters=params,
        input_shot_count=shots,
        confidence=confidence or {},
        runtime_seconds=time.perf_counter() - started,
        warnings=warnings or [],
        configuration_hash=hash_config({"method": method, **params}),
    )


def most_frequent_string(counts: Mapping[str, int]) -> RecoveryCandidate:
    started = time.perf_counter()
    strings, values, _ = _matrix(counts)
    maximum = int(values.max())
    tied = [s for s, value in zip(strings, values, strict=True) if value == maximum]
    chosen = min(tied)
    return _candidate(
        "most_frequent",
        chosen,
        int(values.sum()),
        started,
        confidence={"observed_frequency": maximum / int(values.sum()), "tie_count": len(tied)},
        warnings=["Lexicographic tie-break applied"] if len(tied) > 1 else [],
    )


def bitwise_majority_string(
    counts: Mapping[str, int], *, tie_policy: TiePolicy = "uncertain_zero"
) -> RecoveryCandidate:
    started = time.perf_counter()
    _, values, bits = _matrix(counts)
    shots = int(values.sum())
    p1 = (bits.T @ values.astype(np.float64)) / shots
    tied = np.flatnonzero(np.isclose(p1, 0.5, rtol=0, atol=1e-12)).tolist()
    fallback = "1" if tie_policy in {"one", "uncertain_one"} else "0"
    candidate = "".join("1" if p > 0.5 else "0" if p < 0.5 else fallback for p in p1)
    p0 = 1 - p1
    with np.errstate(divide="ignore", invalid="ignore"):
        entropy = -(np.where(p1 > 0, p1 * np.log2(p1), 0) + np.where(p0 > 0, p0 * np.log2(p0), 0))
    return _candidate(
        "bitwise_majority",
        candidate,
        shots,
        started,
        parameters={"tie_policy": tie_policy},
        confidence={
            "p0": p0.tolist(),
            "p1": p1.tolist(),
            "absolute_margin": np.abs(p1 - p0).tolist(),
            "binary_entropy": entropy.tolist(),
            "uncertain_positions": tied,
        },
        warnings=[f"Ties at {tied}; deterministic fallback={fallback}"] if tied else [],
    )


def weighted_observed_medoid(
    counts: Mapping[str, int], *, exact_threshold: int = 300, approximate_candidates: int = 128
) -> RecoveryCandidate:
    started = time.perf_counter()
    strings, weights, bits = _matrix(counts)
    unique = len(strings)
    exact = unique <= exact_threshold
    if exact:
        candidates = np.arange(unique)
    else:
        ranked = sorted(range(unique), key=lambda i: (-int(weights[i]), strings[i]))
        candidates = np.array(ranked[:approximate_candidates])
    scores = np.empty(len(candidates), dtype=np.float64)
    for out_i, candidate_i in enumerate(candidates):
        scores[out_i] = np.sum(np.count_nonzero(bits[candidate_i] != bits, axis=1) * weights)
    minimum = float(scores.min())
    tied_indices = [int(candidates[i]) for i in np.flatnonzero(scores == minimum)]
    chosen_index = min(tied_indices, key=lambda i: strings[i])
    return _candidate(
        "weighted_observed_medoid",
        strings[chosen_index],
        int(weights.sum()),
        started,
        parameters={
            "exact_threshold": exact_threshold,
            "approximate_candidates": approximate_candidates,
            "exact": exact,
        },
        confidence={"weighted_hamming_objective": minimum, "unique_strings": unique},
        warnings=[] if exact else ["Deterministic top-frequency candidate approximation used"],
    )


def cluster_consensus(
    counts: Mapping[str, int],
    *,
    linkage_method: str = "average",
    distance_threshold: float = 0.15,
    minimum_cluster_weight: float = 0.0,
    tie_policy: TiePolicy = "uncertain_zero",
    exact_threshold: int = 300,
) -> RecoveryCandidate:
    started = time.perf_counter()
    strings, weights, bits = _matrix(counts)
    shots = int(weights.sum())
    approximate = len(strings) > exact_threshold
    if approximate:
        selected_indices = sorted(
            range(len(strings)), key=lambda i: (-int(weights[i]), strings[i])
        )[:exact_threshold]
        strings = [strings[i] for i in selected_indices]
        weights = weights[selected_indices]
        bits = bits[selected_indices]
    if len(strings) == 1:
        labels = np.array([1])
    else:
        labels = fcluster(
            linkage(pdist(bits, metric="hamming"), method=linkage_method),
            distance_threshold,
            criterion="distance",
        )
    cluster_weights = {
        int(label): int(weights[labels == label].sum()) for label in np.unique(labels)
    }
    eligible = [
        label
        for label, weight in cluster_weights.items()
        if weight / shots >= minimum_cluster_weight
    ]
    if not eligible:
        raise ValueError("No cluster satisfies minimum_cluster_weight")
    selected = min(eligible, key=lambda label: (-cluster_weights[label], label))
    mask = labels == selected
    selected_bits = bits[mask]
    selected_weights = weights[mask]
    p1 = (selected_bits.T @ selected_weights.astype(float)) / selected_weights.sum()
    fallback = "1" if tie_policy in {"one", "uncertain_one"} else "0"
    candidate = "".join("1" if p > 0.5 else "0" if p < 0.5 else fallback for p in p1)
    center = np.array([ch == "1" for ch in candidate], dtype=np.uint8)
    mean_distance = float(
        np.average(np.count_nonzero(selected_bits != center, axis=1), weights=selected_weights)
    )
    tied = np.flatnonzero(np.isclose(p1, 0.5, rtol=0, atol=1e-12)).tolist()
    return _candidate(
        "cluster_consensus",
        candidate,
        shots,
        started,
        parameters={
            "linkage_method": linkage_method,
            "distance_threshold": distance_threshold,
            "minimum_cluster_weight": minimum_cluster_weight,
            "tie_policy": tie_policy,
            "exact_threshold": exact_threshold,
            "exact": not approximate,
        },
        confidence={
            "number_of_clusters": len(cluster_weights),
            "cluster_weights": cluster_weights,
            "selected_cluster": selected,
            "within_cluster_mean_hamming_distance": mean_distance,
            "selected_cluster_fraction": cluster_weights[selected] / shots,
            "uncertain_positions": tied,
        },
        warnings=(
            ["Deterministic top-frequency clustering approximation used"] if approximate else []
        )
        + ([f"Tied cluster-consensus bits at {tied}"] if tied else []),
    )


def method_agreement(candidates: list[RecoveryCandidate]) -> dict[str, object]:
    if not candidates:
        raise ValueError("At least one candidate is required")
    n = candidates[0].number_of_qubits
    if any(c.number_of_qubits != n for c in candidates):
        raise ValueError("Candidate lengths differ")
    matrix = [
        [
            sum(a != b for a, b in zip(x.canonical_bitstring, y.canonical_bitstring, strict=True))
            for y in candidates
        ]
        for x in candidates
    ]
    columns = list(zip(*(c.canonical_bitstring for c in candidates), strict=True))
    disagree = [i for i, column in enumerate(columns) if len(set(column)) > 1]
    consensus = "".join("1" if column.count("1") > len(column) / 2 else "0" for column in columns)
    return {
        "methods": [c.method_name for c in candidates],
        "pairwise_hamming_distance": matrix,
        "pairwise_percentage_agreement": [[100 * (n - d) / n for d in row] for row in matrix],
        "disagreement_positions": disagree,
        "consensus": consensus,
        "low_confidence_positions": disagree,
    }


def score_candidate(candidate: str, target: str, *, require_p12: bool = True) -> TargetScore:
    if len(candidate) != len(target):
        raise ValueError("Candidate and target lengths differ")
    if require_p12 and len(target) != 98:
        raise ValueError("P12 scores require exactly 98 bits")
    if set(candidate + target) - {"0", "1"}:
        raise ValueError("Scoring requires canonical binary strings")
    incorrect = tuple(i for i, (a, b) in enumerate(zip(candidate, target, strict=True)) if a != b)
    correct = len(target) - len(incorrect)
    return TargetScore(
        not incorrect,
        correct,
        len(target),
        correct / len(target),
        100 * correct / len(target),
        len(incorrect),
        incorrect,
    )


def score_as_dict(candidate: str, target: str) -> dict[str, object]:
    return asdict(score_candidate(candidate, target))
