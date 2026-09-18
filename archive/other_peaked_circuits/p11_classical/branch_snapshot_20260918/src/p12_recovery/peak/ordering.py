"""Answer-blind weighted interaction orderings for P6 diagnostics."""

from __future__ import annotations

import numpy as np

from .qasm import PeakQASM


def edge_weights(circuit: PeakQASM) -> dict[tuple[int, int], int]:
    weights: dict[tuple[int, int], int] = {}
    for gate in circuit.gates:
        if len(gate.qubits) == 2:
            edge = tuple(sorted(gate.qubits))
            weights[edge] = weights.get(edge, 0) + 1
    return weights


def weighted_routing_proxy(circuit: PeakQASM, order: list[int]) -> dict[str, float | int]:
    if sorted(order) != list(range(circuit.n_qubits)):
        raise ValueError("order must contain every logical qubit exactly once")
    position = {qubit: index for index, qubit in enumerate(order)}
    weighted_bandwidth = 0
    max_bandwidth = 0
    for (left, right), weight in edge_weights(circuit).items():
        distance = abs(position[left] - position[right])
        weighted_bandwidth += weight * distance
        max_bandwidth = max(max_bandwidth, distance)
    return {"weighted_bandwidth": weighted_bandwidth, "max_bandwidth": max_bandwidth, "edge_count": len(edge_weights(circuit))}


def _spectral_order(circuit: PeakQASM) -> list[int]:
    n = circuit.n_qubits
    matrix = np.zeros((n, n), dtype=float)
    for (left, right), weight in edge_weights(circuit).items():
        matrix[left, right] += weight
        matrix[right, left] += weight
    laplacian = np.diag(matrix.sum(axis=1)) - matrix
    values, vectors = np.linalg.eigh(laplacian)
    index = 1 if n > 1 and values[1] > 1e-12 else 0
    return [int(qubit) for qubit in np.argsort(vectors[:, index], kind="stable")]


def _greedy_heavy_order(circuit: PeakQASM) -> list[int]:
    weights = edge_weights(circuit)
    neighbors: dict[int, dict[int, int]] = {q: {} for q in range(circuit.n_qubits)}
    for (left, right), weight in weights.items():
        neighbors[left][right] = weight
        neighbors[right][left] = weight
    start = max(neighbors, key=lambda q: (sum(neighbors[q].values()), -q))
    order = [start]
    remaining = set(range(circuit.n_qubits)) - {start}
    while remaining:
        candidate = max(remaining, key=lambda q: (sum(neighbors[q].get(item, 0) for item in order[-3:]), sum(neighbors[q].values()), -q))
        order.append(candidate)
        remaining.remove(candidate)
    return order


def compare_orderings(circuit: PeakQASM) -> dict[str, object]:
    identity = list(range(circuit.n_qubits))
    spectral = _spectral_order(circuit)
    heavy = _greedy_heavy_order(circuit)
    try:
        import networkx as nx

        graph = nx.Graph()
        graph.add_nodes_from(range(circuit.n_qubits))
        graph.add_weighted_edges_from((left, right, weight) for (left, right), weight in edge_weights(circuit).items())
        # NetworkX 3.6's RCM implementation is topology-only; weighted
        # interaction cost is still evaluated by weighted_routing_proxy below.
        rcm = list(nx.utils.reverse_cuthill_mckee_ordering(graph))
    except ImportError:
        rcm = identity
    orders = {"identity": identity, "spectral": spectral, "heavy_greedy": heavy, "rcm": rcm}
    metrics = {name: weighted_routing_proxy(circuit, order) for name, order in orders.items()}
    best = min(metrics, key=lambda name: (metrics[name]["weighted_bandwidth"], name))
    return {"answer_blind": True, "orders": orders, "metrics": metrics, "best_ordering": best}
