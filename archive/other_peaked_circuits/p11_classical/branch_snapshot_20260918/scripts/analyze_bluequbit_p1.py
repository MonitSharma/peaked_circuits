#!/usr/bin/env python3
"""Blind, input-only forensics for a BlueQubit peaked-circuit QASM.

This tool never reads an expected bitstring.  It reports basic statistics,
weighted/unweighted interaction metrics, temporal density, cut candidates, and
ordering proxies suitable for selecting bounded follow-up experiments.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from structural.qasm_events import parse_qasm


def _graph_metrics(circuit):
    pairs = Counter(tuple(sorted(event.wires)) for event in circuit.two_qubit)
    partners = {q: set() for q in range(circuit.n_qubits)}
    weighted = Counter()
    for (a, b), count in pairs.items():
        partners[a].add(b); partners[b].add(a)
        weighted[a] += count; weighted[b] += count
    degrees = [len(partners[q]) for q in range(circuit.n_qubits)]
    weighted_degrees = [weighted[q] for q in range(circuit.n_qubits)]
    possible = circuit.n_qubits * (circuit.n_qubits - 1) // 2
    return {
        "unique_interacting_pairs": len(pairs),
        "mean_degree": statistics.mean(degrees),
        "median_degree": statistics.median(degrees),
        "max_degree": max(degrees, default=0),
        "graph_density": len(pairs) / possible if possible else 0.0,
        "connected_components": _components(circuit.n_qubits, pairs),
        "mean_weighted_degree": statistics.mean(weighted_degrees),
        "max_weighted_degree": max(weighted_degrees, default=0),
        "weighted_degree_distribution": weighted_degrees,
        "unweighted_degree_distribution": degrees,
        "total_two_qubit_interaction_count": len(circuit.two_qubit),
        "interaction_frequency_distribution": dict(sorted(Counter(pairs.values()).items())),
    }


def _components(n, pairs):
    graph = {q: set() for q in range(n)}
    for a, b in pairs:
        graph[a].add(b); graph[b].add(a)
    seen = set(); components = []
    for start in range(n):
        if start in seen: continue
        stack = [start]; seen.add(start); size = 0
        while stack:
            q = stack.pop(); size += 1
            for other in graph[q] - seen:
                seen.add(other); stack.append(other)
        components.append(size)
    return sorted(components, reverse=True)


def _ordering_rows(circuit):
    pairs = Counter(tuple(sorted(event.wires)) for event in circuit.two_qubit)
    weighted_degree = Counter()
    for (a, b), count in pairs.items():
        weighted_degree[a] += count; weighted_degree[b] += count
    orderings = {
        "original": list(range(circuit.n_qubits)),
        "reversed": list(reversed(range(circuit.n_qubits))),
        "weighted_degree_desc": sorted(range(circuit.n_qubits), key=lambda q: (-weighted_degree[q], q)),
        "weighted_degree_asc": sorted(range(circuit.n_qubits), key=lambda q: (weighted_degree[q], q)),
    }
    adjacency = np.zeros((circuit.n_qubits, circuit.n_qubits), dtype=float)
    for (a, b), count in pairs.items():
        adjacency[a, b] = adjacency[b, a] = count
    degree_matrix = np.diag(adjacency.sum(axis=1))
    eigenvalues, eigenvectors = np.linalg.eigh(degree_matrix - adjacency)
    fiedler = eigenvectors[:, 1] if len(eigenvalues) > 1 else np.arange(circuit.n_qubits)
    orderings["fiedler"] = sorted(range(circuit.n_qubits), key=lambda q: (fiedler[q], q))
    try:
        from scipy.sparse.csgraph import reverse_cuthill_mckee
        orderings["rcm"] = reverse_cuthill_mckee(adjacency, symmetric_mode=True).tolist()
    except Exception:
        orderings["rcm"] = list(range(circuit.n_qubits))
    rows = []
    for name, order in orderings.items():
        site = {q: i for i, q in enumerate(order)}
        spans = [abs(site[a] - site[b]) for a, b in pairs]
        cut = [0] * (circuit.n_qubits - 1)
        for (a, b), count in pairs.items():
            lo, hi = sorted((site[a], site[b]))
            for boundary in range(lo, hi): cut[boundary] += count
        rows.append({"ordering": name, "weighted_edge_span": sum(abs(site[a]-site[b])*c for (a,b),c in pairs.items()),
                     "mean_interaction_span": statistics.mean(spans) if spans else 0.0,
                     "max_interaction_span": max(spans, default=0), "max_weighted_cut": max(cut, default=0),
                     "weighted_cut_profile": cut, "order": order})
    return rows


def _cut_rows(circuit, ratios):
    q2 = circuit.two_qubit
    rows = []
    for ratio in ratios:
        cut = int(round(ratio * len(q2)))
        left = q2[:cut]; right = q2[cut:]
        left_pairs = {tuple(sorted(e.wires)) for e in left}
        right_pairs = {tuple(sorted(e.wires)) for e in right}
        overlap = len(left_pairs & right_pairs)
        left_counts = Counter(tuple(sorted(e.wires)) for e in left)
        right_counts = Counter(tuple(sorted(e.wires)) for e in right)
        cosine = 0.0
        keys = set(left_counts) | set(right_counts)
        if keys:
            a = np.array([left_counts[k] for k in keys], dtype=float)
            b = np.array([right_counts[k] for k in keys], dtype=float)
            denom = np.linalg.norm(a) * np.linalg.norm(b)
            cosine = float(np.dot(a, b) / denom) if denom else 0.0
        rows.append({"ratio": ratio, "cut_q2_index": cut, "left_q2": cut, "right_q2": len(q2)-cut,
                     "unique_pair_overlap": overlap, "weighted_pair_cosine": cosine})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qasm", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    circuit = parse_qasm(args.qasm)
    events_by_gate = Counter(e.gate for e in circuit.events)
    layers = max((e.layer for e in circuit.events), default=-1) + 1
    q2_layers = defaultdict(list)
    for e in circuit.two_qubit: q2_layers[e.layer].append(e)
    out = args.output; out.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(args.qasm.read_bytes()).hexdigest()
    result = {"schema": "bluequbit-p1-forensics-v1", "qasm": str(args.qasm), "qasm_sha256": fingerprint,
              "file_size_bytes": args.qasm.stat().st_size, "n_qubits": circuit.n_qubits,
              "n_events": len(circuit.events), "gate_counts": dict(sorted(events_by_gate.items())),
              "one_qubit_count": sum(len(e.wires)==1 for e in circuit.events),
              "two_qubit_count": len(circuit.two_qubit), "circuit_depth": layers,
              "two_qubit_depth": len(q2_layers), "two_qubit_layer_occupancy": {str(k): len(v) for k,v in q2_layers.items()},
              "interaction_graph": _graph_metrics(circuit),
              "temporal_quarter_counts": [sum(1 for e in circuit.two_qubit if i*4*len(circuit.two_qubit)//4 <= (e.q2_index or 0) < (i+1)*len(circuit.two_qubit)//4) for i in range(4)],
              "ordering_proxies": _ordering_rows(circuit), "blindness": "No expected output or oracle read."}
    (out / "AUDIT.json").write_text(json.dumps(result, indent=2) + "\n")
    ratios = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    with (out / "cut_scan.csv").open("w", newline="") as handle:
        rows = _cut_rows(circuit, ratios); writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    with (out / "ordering_proxies.csv").open("w", newline="") as handle:
        rows = _ordering_rows(circuit); fields = ["ordering", "weighted_edge_span", "mean_interaction_span", "max_interaction_span", "max_weighted_cut"]; writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows({field: row[field] for field in fields} for row in rows)
    print(json.dumps({"qasm_sha256": fingerprint, "n_qubits": circuit.n_qubits, "two_qubit_count": len(circuit.two_qubit), "depth": layers}, indent=2))


if __name__ == "__main__": main()
