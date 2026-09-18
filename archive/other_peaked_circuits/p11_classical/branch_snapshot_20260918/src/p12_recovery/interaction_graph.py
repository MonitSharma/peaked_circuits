from __future__ import annotations

from collections import Counter

import networkx as nx
import numpy as np

from .models import InteractionGraphStatistics
from .qasm_io import ParsedQASM


def build_interaction_graph(circuit: ParsedQASM) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(circuit.number_of_qubits))
    for operation in circuit.operations:
        if len(operation.qubits) == 2 and operation.name != "measure":
            a, b = sorted(operation.qubits)
            if graph.has_edge(a, b):
                graph[a][b]["weight"] += 1
            else:
                graph.add_edge(a, b, weight=1)
    return graph


def interaction_statistics(graph: nx.Graph, *, top_n: int = 20) -> InteractionGraphStatistics:
    active = [node for node, degree in graph.degree() if degree]
    degrees = np.array([degree for _, degree in graph.degree()], dtype=float)
    weighted = np.array([degree for _, degree in graph.degree(weight="weight")], dtype=float)
    components = sorted(nx.connected_components(graph), key=lambda item: (-len(item), min(item)))
    nontrivial = [graph.subgraph(component) for component in components if len(component) > 1]
    fully_connected = nx.is_connected(graph) if graph.number_of_nodes() else False
    diameter = nx.diameter(graph) if fully_connected else None
    component_diameters = [
        nx.diameter(component) if len(component) > 1 else 0
        for component in (graph.subgraph(c) for c in components)
    ]
    average_path = nx.average_shortest_path_length(graph) if fully_connected else None
    pairs = sorted(
        ((a, b, data["weight"]) for a, b, data in graph.edges(data=True)),
        key=lambda item: (-item[2], item[0], item[1]),
    )[:top_n]
    del nontrivial

    def stats(values: np.ndarray) -> tuple[float, float, float, float]:
        return (
            float(values.min()) if len(values) else 0.0,
            float(values.mean() if len(values) else 0),
            float(np.median(values) if len(values) else 0),
            float(values.max()) if len(values) else 0.0,
        )

    d_min, d_mean, d_median, d_max = stats(degrees)
    w_min, w_mean, w_median, w_max = stats(weighted)
    return InteractionGraphStatistics(
        number_of_nodes=graph.number_of_nodes(),
        active_nodes=len(active),
        number_of_edges=graph.number_of_edges(),
        density=nx.density(graph),
        connected_components=len(components),
        component_sizes=[len(c) for c in components],
        degree_min=d_min,
        degree_mean=d_mean,
        degree_median=d_median,
        degree_max=d_max,
        degree_histogram={
            str(int(value)): int(np.count_nonzero(degrees == value))
            for value in sorted(set(degrees.tolist()))
        },
        weighted_degree_min=w_min,
        weighted_degree_mean=w_mean,
        weighted_degree_median=w_median,
        weighted_degree_max=w_max,
        diameter=diameter,
        component_diameters=component_diameters,
        average_shortest_path_length=average_path,
        frequent_pairs=[{"qubits": [a, b], "count": weight} for a, b, weight in pairs],
        fully_connected=fully_connected,
        all_qubits_participate=len(active) == graph.number_of_nodes(),
    )


def pair_frequencies(graph: nx.Graph) -> Counter[tuple[int, int]]:
    return Counter({(a, b): int(data["weight"]) for a, b, data in graph.edges(data=True)})
