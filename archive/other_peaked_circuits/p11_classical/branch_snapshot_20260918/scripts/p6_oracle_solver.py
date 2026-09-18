"""Solve and design quantitative Hamming-overlap queries for P6.

The overlap table is deliberately treated as an oracle-assisted input.  This
module never claims that post-hoc scores are available during answer-blind
simulation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass(frozen=True)
class Observation:
    candidate: str
    score: int


def overlap(candidate: str, target: str) -> int:
    if len(candidate) != len(target):
        raise ValueError("candidate and target lengths differ")
    return sum(a == b for a, b in zip(candidate, target, strict=True))


def errors_in_subset(baseline: str, baseline_score: int, subset: list[int], score: int) -> int:
    """Return the exact number of baseline errors in a flipped subset."""
    return (score - baseline_score + len(subset)) // 2


def _constraint(observations: list[Observation]) -> tuple[np.ndarray, np.ndarray]:
    n = len(observations[0].candidate)
    matrix = []
    rhs = []
    for item in observations:
        bits = np.asarray([int(bit) for bit in item.candidate], dtype=float)
        # overlap(x, a) = n - sum(a) + sum((2a-1)x)
        matrix.append(2.0 * bits - 1.0)
        rhs.append(item.score - n + int(bits.sum()))
    return np.asarray(matrix), np.asarray(rhs, dtype=float)


def _solve(observations: list[Observation], objective: np.ndarray | None = None,
           maximize: bool = False) -> str:
    matrix, rhs = _constraint(observations)
    n = matrix.shape[1]
    if objective is None:
        objective = np.zeros(n)
    result = milp(
        c=(-objective if maximize else objective),
        integrality=np.ones(n),
        bounds=Bounds(np.zeros(n), np.ones(n)),
        constraints=LinearConstraint(matrix, rhs, rhs),
        options={"time_limit": 60},
    )
    if not result.success:
        raise RuntimeError(f"MILP did not find a feasible target: {result.message}")
    return "".join(str(int(round(value))) for value in result.x)


def certify(observations: list[Observation]) -> dict:
    candidate = _solve(observations)
    n = len(candidate)
    ranges = []
    for index in range(n):
        vector = np.zeros(n)
        vector[index] = 1
        low = int(_solve(observations, vector, maximize=False)[index])
        high = int(_solve(observations, vector, maximize=True)[index])
        ranges.append([low, high])
    return {
        "n_bits": n,
        "n_observations": len(observations),
        "one_feasible_target": candidate,
        "bit_ranges": ranges,
        "uniquely_certified_bits": [i for i, (low, high) in enumerate(ranges) if low == high],
    }


def flipped_query(baseline: str, indices: list[int]) -> str:
    result = list(baseline)
    for index in indices:
        result[index] = "1" if result[index] == "0" else "0"
    return "".join(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.observations.read_text())
    observations = [Observation(item["candidate"], int(item["score"])) for item in raw]
    report = certify(observations)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
