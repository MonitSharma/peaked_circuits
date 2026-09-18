"""Native interaction-graph tensor state with 2-norm BP compression."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import quimb.tensor as qtn
from quimb.tensor.belief_propagation import compress_d2bp

from .native_graph import NativeGraph


ISWAP = np.array(
    [[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]],
    dtype=np.complex128,
)


@dataclass
class NativeGraphState:
    """A graph tensor state whose only virtual bonds are native graph edges."""

    graph: NativeGraph
    max_bond: int
    cutoff: float

    def __post_init__(self) -> None:
        if self.max_bond < 1 or self.cutoff < 0:
            raise ValueError("max_bond must be positive and cutoff non-negative")
        self.physical_inds = tuple(f"p{q}" for q in range(self.graph.n_qubits))
        self.edge_inds = {
            edge: f"e{edge[0]}_{edge[1]}" for edge in self.graph.edges
        }
        tensors = []
        neighbors = {q: [] for q in range(self.graph.n_qubits)}
        for left, right in self.graph.edges:
            neighbors[left].append((right, self.edge_inds[(left, right)]))
            neighbors[right].append((left, self.edge_inds[(left, right)]))
        for q in range(self.graph.n_qubits):
            inds = [self.physical_inds[q]] + [ind for _, ind in neighbors[q]]
            array = np.zeros((2,) + (1,) * (len(inds) - 1), dtype=np.complex128)
            array[(0,) + (0,) * (len(inds) - 1)] = 1.0
            tensors.append(qtn.Tensor(array, inds=inds, tags={f"Q{q}"}))
        self.tn = qtn.TensorNetwork(tensors)
        self.compression_history: list[dict[str, float | int | bool]] = []

    def apply_one(self, matrix: np.ndarray, qubit: int) -> None:
        self.tn = self.tn.gate_inds(
            np.asarray(matrix, dtype=np.complex128),
            [self.physical_inds[qubit]],
            contract=True,
            inplace=False,
        )

    def apply_iswap(self, left: int, right: int) -> None:
        edge = tuple(sorted((left, right)))
        if edge not in self.edge_inds:
            raise ValueError(f"native iSWAP edge {edge} is absent from graph")
        updated = self.tn.gate_inds(
            ISWAP,
            [self.physical_inds[left], self.physical_inds[right]],
            contract="split",
            inplace=False,
        )
        left_tensor = next(t for t in updated if f"Q{left}" in t.tags)
        right_tensor = next(t for t in updated if f"Q{right}" in t.tags)
        shared = set(left_tensor.inds) & set(right_tensor.inds)
        shared.discard(self.physical_inds[left])
        shared.discard(self.physical_inds[right])
        if len(shared) != 1:
            raise RuntimeError(f"native edge split did not produce one bond for {edge}")
        new_edge = next(iter(shared))
        if new_edge != self.edge_inds[edge]:
            updated.reindex({new_edge: self.edge_inds[edge]}, inplace=True)
        self.tn = updated

    def environment_compress(self) -> dict[str, float | int | bool]:
        """Compress all virtual bonds using Quimb's 2-norm BP environment."""
        before = int(max((max(t.shape) for t in self.tn.tensors), default=1))
        if all(self.tn.ind_size(ind) <= 1 for ind in self.edge_inds.values()):
            row = {"max_tensor_axis_before": before, "max_tensor_axis_after": before,
                   "bp_info_present": False, "bp_skipped_product_bonds": True}
            self.compression_history.append(row)
            return row
        info: dict[str, object] = {}
        self.tn = compress_d2bp(
            self.tn,
            max_bond=self.max_bond,
            cutoff=self.cutoff,
            cutoff_mode="rsum2",
            normalize=None,
            output_inds=self.physical_inds,
            max_iterations=100,
            tol=1e-5,
            damping=0.1,
            local_convergence=True,
            optimize="greedy",
            info=info,
            progbar=False,
            inplace=False,
        )
        after = int(max((max(t.shape) for t in self.tn.tensors), default=1))
        finite = all(np.isfinite(t.data).all() for t in self.tn.tensors)
        if not finite:
            raise FloatingPointError("2-norm BP compression produced non-finite tensor data")
        row: dict[str, float | int | bool] = {
            "max_tensor_axis_before": before,
            "max_tensor_axis_after": after,
            "bp_info_present": bool(info),
            "bp_finite": finite,
        }
        self.compression_history.append(row)
        return row

    def norm(self) -> float:
        value = float(np.real(self.tn.H @ self.tn))
        if not np.isfinite(value):
            raise FloatingPointError("state norm is non-finite")
        return value

    def graph_degree(self, qubit: int) -> int:
        return sum(qubit in edge for edge in self.edge_inds)

    def copy(self) -> "NativeGraphState":
        child = object.__new__(NativeGraphState)
        child.graph = self.graph
        child.max_bond = self.max_bond
        child.cutoff = self.cutoff
        child.physical_inds = self.physical_inds
        child.edge_inds = dict(self.edge_inds)
        child.tn = self.tn.copy(deep=True)
        child.compression_history = list(self.compression_history)
        return child

    def project_bit(self, qubit: int, bit: int) -> "NativeGraphState":
        """Project one physical bit, then canonically regauge the child network."""
        if bit not in (0, 1):
            raise ValueError("bit must be 0 or 1")
        child = self.copy()
        physical = child.physical_inds[qubit]
        tensor = next(t for t in child.tn if f"Q{qubit}" in t.tags)
        tensor.modify(data=np.take(tensor.data, bit, axis=0),
                      inds=tensor.inds[1:])
        child.tn.gauge_all_canonize(max_iterations=2, gauge_smudge=1e-8, inplace=True)
        return child

    def amplitudes(self) -> np.ndarray:
        """Return the dense state, for small exact-control circuits only."""
        tensor = self.tn.contract(output_inds=self.physical_inds)
        return np.asarray(tensor.data).reshape(-1)

    def max_bond_observed(self) -> int:
        return int(max((self.tn.ind_size(ind) for ind in self.edge_inds.values()), default=1))
