"""Native interaction-graph reconstruction for the original P8 circuit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

from structural.qasm_events import CircuitEvents, parse_qasm


@dataclass(frozen=True)
class NativeGraph:
    n_qubits: int
    edges: tuple[tuple[int, int], ...]
    coordinates: dict[int, tuple[float, float]]
    exact_rectangular_grid: bool
    rectangular_grid_shape: tuple[int, int]
    iswap_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_qubits": self.n_qubits,
            "edge_count": len(self.edges),
            "edges": [list(edge) for edge in self.edges],
            "coordinates": {str(q): list(self.coordinates[q]) for q in range(self.n_qubits)},
            "coordinate_convention": "deterministic planar-layout (row, col), not a claimed rectangular lattice",
            "exact_rectangular_grid": self.exact_rectangular_grid,
            "rectangular_grid_shape": list(self.rectangular_grid_shape),
            "iswap_count": self.iswap_count,
        }


def _interaction_graph(circuit: CircuitEvents) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(circuit.n_qubits))
    graph.add_edges_from(tuple(sorted(event.wires)) for event in circuit.two_qubit)
    return graph


def _is_subgraph_of_rectangular_grid(graph: nx.Graph, rows: int, cols: int) -> bool:
    grid = nx.grid_2d_graph(rows, cols)
    # A subgraph embedding must preserve node degrees as well as edges; the
    # direction below asks whether the grid contains the P8 graph as a subgraph.
    return nx.algorithms.isomorphism.GraphMatcher(grid, graph).subgraph_is_isomorphic()


def reconstruct_native_graph(path: str | Path) -> NativeGraph:
    circuit = parse_qasm(path)
    edges = tuple(sorted({tuple(sorted(event.wires)) for event in circuit.two_qubit}))
    graph = _interaction_graph(circuit)
    iswaps = [event for event in circuit.events if event.gate == "iswap"]
    if any(tuple(sorted(event.wires)) not in edges for event in iswaps):
        raise AssertionError("native iSWAP is not on the reconstructed interaction graph")
    rows, cols = 5, 8
    exact_grid = _is_subgraph_of_rectangular_grid(graph, rows, cols)
    raw = nx.planar_layout(graph, scale=1.0)
    coordinates = {int(q): (float(raw[q][0]), float(raw[q][1])) for q in graph.nodes}
    return NativeGraph(
        n_qubits=circuit.n_qubits,
        edges=edges,
        coordinates=coordinates,
        exact_rectangular_grid=exact_grid,
        rectangular_grid_shape=(rows, cols),
        iswap_count=len(iswaps),
    )
