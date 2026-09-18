"""Manifest and structural profile generation for answer-blind peak inputs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .qasm import parse


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    circuit = parse(path)
    counts = Counter(g.name for g in circuit.gates)
    pairs = Counter(tuple(sorted(g.qubits)) for g in circuit.gates if len(g.qubits) == 2)
    neighbors: dict[int, set[int]] = defaultdict(set)
    for a, b in pairs:
        neighbors[a].add(b)
        neighbors[b].add(a)
    components = []
    unseen = set(range(circuit.n_qubits))
    while unseen:
        root = min(unseen)
        todo = [root]
        unseen.remove(root)
        component = []
        while todo:
            node = todo.pop()
            component.append(node)
            for nxt in neighbors[node] & unseen:
                unseen.remove(nxt)
                todo.append(nxt)
        components.append(sorted(component))
    layers: dict[int, set[int]] = defaultdict(set)
    two_qubit_layers: set[int] = set()
    last: dict[int, int] = {}
    for gate in circuit.gates:
        layer = max((last.get(q, -1) for q in gate.qubits), default=-1) + 1
        for q in gate.qubits:
            last[q] = layer
        layers[layer].add(gate.name)
        if len(gate.qubits) == 2:
            two_qubit_layers.add(layer)
    degrees = [len(neighbors[q]) for q in range(circuit.n_qubits)]
    weighted = [sum(v for (a, b), v in pairs.items() if q in (a, b)) for q in range(circuit.n_qubits)]
    return {
        "schema": "p12-peak-circuit-manifest-v1",
        "problem": path.stem.split("_")[0].upper(),
        "source_qasm_path": str(path.resolve()), "sha256": _sha256(path),
        "source_file_size_bytes": path.stat().st_size,
        "qasm_version": "2.0", "qubit_count": circuit.n_qubits,
        "gate_counts": dict(sorted(counts.items())), "gate_vocabulary": sorted(counts),
        "gate_count": len(circuit.gates), "two_qubit_gate_count": sum(pairs.values()),
        "depth": len(layers), "two_qubit_depth": len(two_qubit_layers),
        "unique_interaction_edges": len(pairs),
        "graph_density": 2 * len(pairs) / (circuit.n_qubits * (circuit.n_qubits - 1)) if circuit.n_qubits > 1 else 0.0,
        "connected_components": components,
        "degree_statistics": {"min": min(degrees, default=0), "mean": sum(degrees) / len(degrees) if degrees else 0, "max": max(degrees, default=0)},
        "weighted_degree_statistics": {"min": min(weighted, default=0), "mean": sum(weighted) / len(weighted) if weighted else 0, "max": max(weighted, default=0)},
        "weighted_edges": [{"qubits": list(pair), "count": count} for pair, count in sorted(pairs.items())],
        "custom_gate_definitions": list(circuit.custom_gates),
        "iswap_direct_handling": "direct_matrix" if "iswap" in counts else "not_present",
        "canonical_logical_bit_order": "q0_first",
        "method_eligibility": {"mps": True, "tno": True, "mpo": True, "geometry": path.stem.upper().startswith("P8")},
        "provenance": {"original_file_preserved": True, "answer_blind": True},
    }


def write_manifests(inputs: dict[str, str | Path], outdir: str | Path) -> None:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for problem, path in inputs.items():
        data = profile(path)
        data["problem"] = problem
        (outdir / f"{problem}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
