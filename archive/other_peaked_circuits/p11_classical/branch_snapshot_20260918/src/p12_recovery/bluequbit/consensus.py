"""Blind evidence aggregation; unresolved bits are never silently filled."""

from __future__ import annotations

from collections import Counter
from typing import Iterable


def bit_evidence(method_bitstrings: dict[str, Iterable[str]], n_bits: int) -> list[dict]:
    rows = []
    for position in range(n_bits):
        values: Counter[str] = Counter()
        methods: dict[str, list[str]] = {}
        for method, strings in method_bitstrings.items():
            unique = sorted({s[position] for s in strings if len(s) == n_bits and s[position] in "01"})
            if unique:
                methods[method] = unique
                for value in unique:
                    values[value] += 1
        if not values:
            classification, selected = "UNRESOLVED", None
        elif len(values) == 1:
            classification, selected = "WEAKLY_SUPPORTED", next(iter(values))
        else:
            classification, selected = "UNRESOLVED", None
        rows.append({"bit_index_msb_string": position, "classification": classification, "selected_value": selected, "value_counts": dict(values), "supporting_methods": methods})
    return rows


def summarize_consensus(method_bitstrings: dict[str, Iterable[str]], n_bits: int) -> dict:
    rows = bit_evidence(method_bitstrings, n_bits)
    return {"schema": "bluequbit-p1-v2-consensus-v1", "blind": True, "n_bits": n_bits, "method_names": sorted(method_bitstrings), "bits": rows, "strongly_supported": sum(r["classification"] == "STRONGLY_SUPPORTED" for r in rows), "weakly_supported": sum(r["classification"] == "WEAKLY_SUPPORTED" for r in rows), "unresolved": sum(r["classification"] == "UNRESOLVED" for r in rows), "full_candidate": None, "decision": "NO_CONVERGED_BLIND_CANDIDATE"}
