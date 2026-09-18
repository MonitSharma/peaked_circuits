"""Rank P6 strings under hard overlap constraints and soft TN marginals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def load_observations(path: Path) -> list[tuple[str, int]]:
    return [(item["candidate"], int(item["score"])) for item in json.loads(path.read_text())]


def load_marginals(path: Path) -> np.ndarray:
    raw = json.loads(path.read_text())
    return np.asarray([float(item["p1"]) for item in raw["per_bit"]], dtype=float)


def constraint_matrix(observations: list[tuple[str, int]]) -> tuple[np.ndarray, np.ndarray]:
    n = len(observations[0][0])
    matrix = []
    rhs = []
    for candidate, score in observations:
        bits = np.asarray([int(bit) for bit in candidate], dtype=float)
        matrix.append(2 * bits - 1)
        rhs.append(score - n + int(bits.sum()))
    return np.asarray(matrix), np.asarray(rhs, dtype=float)


def solve(observations: list[tuple[str, int]], coefficients: np.ndarray) -> str:
    matrix, rhs = constraint_matrix(observations)
    result = milp(
        c=-coefficients,
        integrality=np.ones(len(coefficients)),
        bounds=Bounds(np.zeros(len(coefficients)), np.ones(len(coefficients))),
        constraints=LinearConstraint(matrix, rhs, rhs),
        options={"time_limit": 60},
    )
    if not result.success:
        raise RuntimeError(result.message)
    return "".join(str(int(round(value))) for value in result.x)


def log_likelihood(candidate: str, marginals: np.ndarray) -> float:
    p = np.clip(marginals, 1e-6, 1 - 1e-6)
    bits = np.asarray([int(bit) for bit in candidate])
    return float(np.sum(bits * np.log(p) + (1 - bits) * np.log1p(-p)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--d128", type=Path, required=True)
    parser.add_argument("--d512", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=200)
    args = parser.parse_args()

    observations = load_observations(args.observations)
    d128 = load_marginals(args.d128)
    d512 = load_marginals(args.d512)
    if len(d128) != len(observations[0][0]) or len(d512) != len(d128):
        raise ValueError("marginal and candidate widths differ")
    logits = [np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1)) for p in (d128, d512)]
    rng = np.random.default_rng(123)
    candidates: set[str] = set()
    mixes = np.linspace(0, 1, 11)
    for weight in mixes:
        base = weight * logits[0] + (1 - weight) * logits[1]
        candidates.add(solve(observations, base))
        for _ in range(max(1, args.samples // len(mixes))):
            candidates.add(solve(observations, base + rng.normal(0, 0.20, len(base))))

    ranked = []
    for candidate in candidates:
        ranked.append({
            "candidate": candidate,
            "combined_log_likelihood": log_likelihood(candidate, 0.5 * (d128 + d512)),
            "d128_log_likelihood": log_likelihood(candidate, d128),
            "d512_log_likelihood": log_likelihood(candidate, d512),
            "overlaps": [sum(a == b for a, b in zip(candidate, target, strict=True)) for target, _ in observations],
            "distance_to_A8": sum(a != b for a, b in zip(candidate, observations[7][0], strict=True)),
        })
    ranked.sort(key=lambda item: item["combined_log_likelihood"], reverse=True)
    report = {
        "n_observations": len(observations),
        "n_unique_feasible_candidates_sampled": len(ranked),
        "method": "recorded hard Hamming constraints; D128/D512 marginals as soft log-likelihood priors",
        "ranked": ranked,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "ranked"}, indent=2))
    for index, item in enumerate(ranked[:20], 1):
        print(index, item["combined_log_likelihood"], item["candidate"], item["overlaps"])


if __name__ == "__main__":
    main()
