"""Candidate-set consensus that does not double-count approximation rungs."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable


def consensus(runs: Iterable[dict]) -> dict:
    families: dict[str, set[str]] = defaultdict(set)
    for run in runs:
        candidate = run.get("candidate") or run.get("bitstring")
        family = run.get("method_family", "unknown")
        if candidate:
            families[family].add(candidate)
    votes: dict[str, int] = defaultdict(int)
    for candidates in families.values():
        for candidate in candidates:
            votes[candidate] += 1
    ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
    return {"method_families": {k: sorted(v) for k, v in families.items()}, "ranked": ranked, "independent_family_count": len(families), "candidate": ranked[0][0] if ranked else None, "status": "CROSS_METHOD_CONVERGED_CANDIDATE" if ranked and ranked[0][1] >= 2 else "PROMISING_CANDIDATE_FAMILY" if ranked else "UNCONVERGED"}
