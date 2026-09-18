#!/usr/bin/env python3
"""Answer-blind Clifford/residual-Pauli feasibility diagnostic for P6.

This is deliberately a diagnostic, not a CAMPS simulator.  It keeps the
Clifford frame in the binary symplectic representation and records the Pauli
supports of residual RZ/RY rotations after Clifford conjugation.  No target
bitstring is loaded or used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from structural.qasm_events import Event, parse_qasm


def _bits_for_pauli(n: int, kind: str, qubit: int) -> int:
    if kind == "rz":
        return 1 << (n + qubit)
    if kind == "ry":
        return (1 << qubit) | (1 << (n + qubit))
    raise ValueError(kind)


def _apply_generator_transform(vector: int, n: int, kind: str, qubit: int) -> int:
    """Apply the GF(2) support map of the inverse Clifford generator.

    Signs are intentionally omitted because the diagnostic only studies
    support/rank complexity.  RZ(k*pi/2) maps like S for odd k; RY(pi/2)
    maps like H.  CZ is self-inverse.
    """
    x = vector & ((1 << n) - 1)
    z = (vector >> n) & ((1 << n) - 1)
    if kind == "h" or kind == "ry_quarter":
        bit = 1 << int(qubit)  # type: ignore[arg-type]
        old_x = vector & ((1 << n) - 1)
        old_z = (vector >> n) & ((1 << n) - 1)
        x = (old_x & ~bit) | (old_z & bit)
        z = (old_z & ~bit) | (old_x & bit)
    elif kind in {"s", "rz_quarter"}:
        bit = 1 << int(qubit)  # type: ignore[arg-type]
        z ^= x & bit
    elif kind == "sx_quarter":
        bit = 1 << int(qubit)  # type: ignore[arg-type]
        x ^= z & bit
    elif kind == "cz":
        # X_a -> X_a Z_b and X_b -> Z_a X_b.
        a, b = qubit
        ba, bb = 1 << a, 1 << b
        if x & ba:
            z ^= bb
        if x & bb:
            z ^= ba
    else:
        raise ValueError(kind)
    return x | (z << n)


def _apply_frame(images: list[int], n: int, kind: str, qubit: int | tuple[int, int]) -> list[int]:
    """Compose the current C^dagger map with a Clifford generator."""
    out: list[int] = []
    for basis in range(2 * n):
        vector = 1 << basis
        if kind == "cz":
            transformed = _apply_generator_transform(vector, n, kind, qubit)  # type: ignore[arg-type]
        else:
            transformed = _apply_generator_transform(vector, n, kind, qubit)  # type: ignore[arg-type]
        mapped = 0
        while transformed:
            low = transformed & -transformed
            mapped ^= images[low.bit_length() - 1]
            transformed ^= low
        out.append(mapped)
    return out


def _map_pauli(images: list[int], vector: int) -> int:
    mapped = 0
    while vector:
        low = vector & -vector
        mapped ^= images[low.bit_length() - 1]
        vector ^= low
    return mapped


def _gf2_rank(vectors: list[int]) -> int:
    pivots: dict[int, int] = {}
    rank = 0
    for value in vectors:
        row = value
        while row:
            pivot = row.bit_length() - 1
            if pivot in pivots:
                row ^= pivots[pivot]
            else:
                pivots[pivot] = row
                rank += 1
                break
    return rank


def _grid_angle(angle: float, tolerance: float) -> tuple[bool, int, float]:
    scaled = angle / (math.pi / 2.0)
    nearest = round(scaled)
    error = abs(angle - nearest * math.pi / 2.0)
    return error <= tolerance, nearest, error


def _rotation_clifford_kind(axis: str, multiple: int) -> str | None:
    if multiple % 2 == 0:
        return None
    return "rz_quarter" if axis == "rz" else "ry_quarter"


def _record_profile(profile: list[dict], event: Event, residuals: list[int], n: int) -> None:
    rank = _gf2_rank(residuals)
    profile.append({
        "event_index": event.index,
        "q2_index": event.q2_index,
        "residual_count": len(residuals),
        "distinct_supports": len(set(residuals)),
        "support_rank": rank,
        "support_nullity_proxy": len(residuals) - rank,
        "max_support_weight": max((v.bit_count() for v in residuals), default=0),
        "mean_support_weight": (
            sum(v.bit_count() for v in residuals) / len(residuals) if residuals else 0.0
        ),
        "n_qubits": n,
    })


def diagnose(path: Path, tolerance: float) -> dict:
    circuit = parse_qasm(path)
    n = circuit.n_qubits
    images = [1 << index for index in range(2 * n)]
    residuals: list[int] = []
    profile: list[dict] = []
    counts = Counter()
    angle_errors: list[float] = []
    merged = 0
    possible_clifford_after_merge = 0
    last_support: int | None = None
    last_run_angle = 0.0

    for event in circuit.events:
        if event.gate == "cz":
            images = _apply_frame(images, n, "cz", event.wires)
            counts["cz_clifford"] += 1
            _record_profile(profile, event, residuals, n)
            continue
        if event.gate != "u":
            counts[f"unsupported_{event.gate}"] += 1
            _record_profile(profile, event, residuals, n)
            continue

        theta, phi, lam = event.params
        # U(theta, phi, lambda) = RZ(phi) RY(theta) RZ(lambda), applied in
        # chronological order as lambda, theta, phi.
        for axis, angle in (("rz", lam), ("ry", theta), ("rz", phi)):
            exact, multiple, error = _grid_angle(angle, tolerance)
            angle_errors.append(error)
            if exact:
                counts["exact_clifford_rotation"] += 1
                kind = _rotation_clifford_kind(axis, multiple)
                if kind is not None:
                    images = _apply_frame(images, n, kind, event.wires[0])
                else:
                    counts["identity_or_pauli_rotation"] += 1
            else:
                counts["residual_rotation"] += 1
                support = _map_pauli(images, _bits_for_pauli(n, axis, event.wires[0]))
                residuals.append(support)
                if support == last_support:
                    merged += 1
                    last_run_angle += angle
                    combined = last_run_angle
                    combined_exact, _, _ = _grid_angle(combined, tolerance)
                    if combined_exact:
                        possible_clifford_after_merge += 1
                else:
                    last_support = support
                    last_run_angle = angle
        counts["u_events"] += 1
        _record_profile(profile, event, residuals, n)

    rank = _gf2_rank(residuals)
    weights = Counter(str(v.bit_count()) for v in residuals)
    return {
        "schema": "p6-clifford-residual-diagnostic-v1",
        "answer_blind": True,
        "source": str(path.resolve()),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "n_qubits": n,
        "event_count": len(circuit.events),
        "two_qubit_count": circuit.n_two_qubit,
        "angle_grid": {"spacing": "pi/2", "absolute_tolerance": tolerance},
        "counts": dict(counts),
        "residual_summary": {
            "raw_residual_rotations": len(residuals),
            "distinct_pauli_supports": len(set(residuals)),
            "support_rank": rank,
            "support_nullity_proxy": len(residuals) - rank,
            "max_support_weight": max((v.bit_count() for v in residuals), default=0),
            "mean_support_weight": sum(v.bit_count() for v in residuals) / len(residuals) if residuals else 0.0,
            "support_weight_distribution": dict(sorted(weights.items(), key=lambda item: int(item[0]))),
            "consecutive_merge_opportunities": merged,
            "merged_runs_reaching_clifford_angle": possible_clifford_after_merge,
        },
        "angle_error_summary": {
            "min": min(angle_errors, default=None),
            "median": sorted(angle_errors)[len(angle_errors) // 2] if angle_errors else None,
            "max": max(angle_errors, default=None),
        },
        "diagnostic_interpretation": (
            "The support_nullity_proxy is a screening statistic, not a proof of CAMPS bond efficiency."
        ),
        "profile": profile,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=1e-8)
    args = parser.parse_args()
    result = diagnose(args.source, args.tolerance)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("source_sha256", "counts", "residual_summary", "angle_error_summary")}, indent=2))


if __name__ == "__main__":
    main()
