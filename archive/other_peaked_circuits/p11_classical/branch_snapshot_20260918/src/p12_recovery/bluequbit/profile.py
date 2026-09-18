"""Answer-blind structural profiling for BlueQubit peaked circuits.

This module deliberately contains no target-bitstring logic.  It uses the
repository's QASM event parser and reports structure useful for choosing
bounded approximate methods.
"""

from __future__ import annotations

import cmath
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

from structural.qasm_events import CircuitEvents, Event, parse_qasm


def _u_matrix(theta: float, phi: float, lam: float) -> np.ndarray:
    c, s = math.cos(theta / 2.0), math.sin(theta / 2.0)
    return np.array(
        [[c, -cmath.exp(1j * lam) * s],
         [cmath.exp(1j * phi) * s, cmath.exp(1j * (phi + lam)) * c]],
        dtype=np.complex128,
    )


def _phase_invariant_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Return Frobenius distance after optimal global-phase alignment."""
    overlap = np.vdot(b, a)
    phase = 1.0 if abs(overlap) == 0 else overlap / abs(overlap)
    return float(np.linalg.norm(a - phase * b, ord="fro") / math.sqrt(2.0))


def _canonical_phase(a: np.ndarray) -> np.ndarray:
    flat = a.ravel()
    pivot = next((z for z in flat if abs(z) > 1e-14), 1.0 + 0j)
    return a * (np.conj(pivot) / abs(pivot))


def single_qubit_cliffords() -> list[np.ndarray]:
    """Generate the 24 projective single-qubit Clifford matrices from H,S."""
    h = np.array([[1, 1], [1, -1]], dtype=np.complex128) / math.sqrt(2.0)
    s = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
    todo = [np.eye(2, dtype=np.complex128)]
    seen: dict[tuple[float, ...], np.ndarray] = {}
    while todo:
        current = todo.pop()
        canonical = _canonical_phase(current)
        key = tuple(np.round(np.concatenate((canonical.real.ravel(), canonical.imag.ravel())), 12))
        if key in seen:
            continue
        seen[key] = canonical
        todo.extend((h @ current, s @ current))
    return list(seen.values())


def _rational_summary(value: float, max_denominator: int = 32) -> dict[str, Any]:
    ratio = value / math.pi
    fraction = Fraction(ratio).limit_denominator(max_denominator)
    error = abs(ratio - float(fraction))
    return {"value_over_pi": ratio, "fraction": f"{fraction.numerator}/{fraction.denominator}", "absolute_error": error}


def clifford_proximity(circuit: CircuitEvents) -> dict[str, Any]:
    cliffords = single_qubit_cliffords()
    rows: list[dict[str, Any]] = []
    distances: list[float] = []
    for event in circuit.events:
        if event.gate != "u":
            continue
        matrix = _u_matrix(*event.params)
        scores = [_phase_invariant_distance(matrix, candidate) for candidate in cliffords]
        nearest = int(np.argmin(scores))
        distance = float(scores[nearest])
        distances.append(distance)
        rows.append({
            "gate_index": event.index,
            "qubit": event.wires[0],
            "theta": event.params[0],
            "phi": event.params[1],
            "lambda": event.params[2],
            "nearest_clifford_index": nearest,
            "distance": distance,
            "theta_rational": _rational_summary(event.params[0]),
            "phi_rational": _rational_summary(event.params[1]),
            "lambda_rational": _rational_summary(event.params[2]),
        })
    values = np.asarray(distances, dtype=float)
    thresholds = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2]
    return {
        "schema": "bluequbit-p1-v2-clifford-proximity-v1",
        "clifford_count": len(cliffords),
        "u_gate_count": len(rows),
        "threshold_counts": {str(t): int(np.count_nonzero(values <= t)) for t in thresholds},
        "threshold_fractions": {str(t): float(np.mean(values <= t)) if len(values) else 0.0 for t in thresholds},
        "distance_summary": {
            "min": float(np.min(values)) if len(values) else None,
            "median": float(np.median(values)) if len(values) else None,
            "mean": float(np.mean(values)) if len(values) else None,
            "max": float(np.max(values)) if len(values) else None,
        },
        "decision": "CLIFFORD_PERTURBATION_WORTH_TESTING" if (len(values) and np.mean(values <= 1e-6) >= 0.1) else "CLIFFORD_PERTURBATION_LOW_PRIORITY",
        "gates": rows,
    }


def _interaction_graph(circuit: CircuitEvents) -> dict[str, Any]:
    counts: dict[tuple[int, int], int] = {}
    for event in circuit.two_qubit:
        pair = tuple(sorted(event.wires))
        counts[pair] = counts.get(pair, 0) + 1
    n = circuit.n_qubits
    degrees = [0] * n
    weighted = [0] * n
    for (a, b), count in counts.items():
        degrees[a] += 1
        degrees[b] += 1
        weighted[a] += count
        weighted[b] += count
    adjacency = {i: set() for i in range(n)}
    for a, b in counts:
        adjacency[a].add(b)
        adjacency[b].add(a)
    components: list[list[int]] = []
    unseen = set(range(n))
    while unseen:
        root = min(unseen)
        stack, component = [root], []
        unseen.remove(root)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node] & unseen:
                unseen.remove(neighbor)
                stack.append(neighbor)
        components.append(sorted(component))
    return {
        "unique_interacting_pairs": len(counts),
        "simple_degree": {"per_qubit": degrees, "mean": float(np.mean(degrees)), "median": float(np.median(degrees)), "max": max(degrees, default=0), "density": 2 * len(counts) / (n * (n - 1)) if n > 1 else 0.0},
        "weighted_interaction_frequency": {"per_qubit": weighted, "mean": float(np.mean(weighted)), "max": max(weighted, default=0), "distribution": {str(v): weighted.count(v) for v in sorted(set(weighted))}},
        "connected_components": components,
        "pair_frequency_distribution": {str(v): list(counts.values()).count(v) for v in sorted(set(counts.values()))},
    }


def _lightcone(circuit: CircuitEvents, output: int) -> dict[str, Any]:
    active = {output}
    rows: list[dict[str, Any]] = []
    for reverse_step, event in enumerate(reversed(circuit.events), 1):
        if not (active & set(event.wires)):
            continue
        active.update(event.wires)
        rows.append({"reverse_event": reverse_step, "gate_index": event.index, "gate": event.gate, "active_qubits": len(active), "u_gates": int(event.gate == "u"), "cz_gates": int(event.gate == "cz")})
    return {"output_qubit": output, "final_active_qubits": len(active), "gates_in_lightcone": len(rows), "u_gates": sum(r["u_gates"] for r in rows), "cz_gates": sum(r["cz_gates"] for r in rows), "trace": rows}


def lightcones(circuit: CircuitEvents) -> dict[str, Any]:
    rows = [_lightcone(circuit, q) for q in range(circuit.n_qubits)]
    complexity = [r["gates_in_lightcone"] + 2 * r["u_gates"] + r["cz_gates"] for r in rows]
    order = np.argsort(complexity)
    panel_positions = np.linspace(0, len(order) - 1, min(8, len(order)), dtype=int)
    panel = [int(order[position]) for position in panel_positions]
    low_count = min(2, len(panel))
    high_count = min(2, max(0, len(panel) - low_count))
    return {"schema": "bluequbit-p1-v2-lightcones-v1", "outputs": rows, "complexity_score": complexity, "initial_pps_panel": {"low": panel[:low_count], "median": panel[low_count:len(panel) - high_count], "high": panel[len(panel) - high_count:] if high_count else []}}


def profile_circuit(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    circuit = parse_qasm(path)
    qasm = path.read_bytes()
    layers = {event.layer for event in circuit.events}
    two_layers = {event.layer for event in circuit.two_qubit}
    counts: dict[str, int] = {}
    for event in circuit.events:
        counts[event.gate] = counts.get(event.gate, 0) + 1
    return {
        "schema": "bluequbit-p1-v2-profile-v1",
        "qasm_path": str(path),
        "qasm_sha256": hashlib.sha256(qasm).hexdigest(),
        "file_size_bytes": len(qasm),
        "n_qubits": circuit.n_qubits,
        "n_events": len(circuit.events),
        "gate_counts": counts,
        "one_qubit_count": sum(len(e.wires) == 1 for e in circuit.events),
        "two_qubit_count": len(circuit.two_qubit),
        "circuit_depth": max(layers, default=-1) + 1,
        "two_qubit_depth": len(two_layers),
        "measurement_count": 0,
        "interaction_graph": _interaction_graph(circuit),
    }


def write_profile_bundle(qasm_path: str | Path, outdir: str | Path) -> None:
    qasm_path, outdir = Path(qasm_path), Path(outdir)
    circuit = parse_qasm(qasm_path)
    outdir.mkdir(parents=True, exist_ok=True)
    base = profile_circuit(qasm_path)
    (outdir / "circuit.json").write_text(json.dumps(base, indent=2) + "\n")
    (outdir / "clifford_proximity.json").write_text(json.dumps(clifford_proximity(circuit), indent=2) + "\n")
    (outdir / "lightcones.json").write_text(json.dumps(lightcones(circuit), indent=2) + "\n")
