"""Bounded tree-tensor-network circuit simulation for sparse peak circuits.

The implementation keeps a binary tree state and updates only the tensor path
between the two leaves touched by a gate.  Every path update is followed by a
local SVD truncation.  It is deliberately small and deterministic: it is a
research route, not a claim that a finite-bond TTN is an exact simulator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .qasm import PeakQASM
from .ttn import TreeNode, build_unweighted_tree, build_weighted_tree


@dataclass(frozen=True)
class TTNDecode:
    bitstring: str
    probability: float
    total_mass: float
    beam_width: int
    nodes_expanded: int


def _tree_index(tree: TreeNode) -> tuple[list[TreeNode], dict[int, int], dict[int, int], dict[int, tuple[int, ...]]]:
    nodes: list[TreeNode] = []
    parent: dict[int, int] = {}
    children: dict[int, tuple[int, ...]] = {}
    leaf_node: dict[int, int] = {}

    def visit(node: TreeNode, parent_id: int | None = None) -> int:
        node_id = len(nodes)
        nodes.append(node)
        if parent_id is not None:
            parent[node_id] = parent_id
        child_ids = tuple(visit(child, node_id) for child in node.children)
        children[node_id] = child_ids
        if not child_ids:
            leaf_node[node.leaves[0]] = node_id
        return node_id

    visit(tree)
    return nodes, parent, leaf_node, children


class TreeTensorState:
    """A binary TTN state with physical indices only at the leaves."""

    def __init__(self, circuit: PeakQASM, *, max_bond: int = 4, cutoff: float = 1e-10, tree_mode: str = "weighted") -> None:
        if max_bond < 1 or cutoff < 0:
            raise ValueError("max_bond must be positive and cutoff non-negative")
        self.n_qubits = circuit.n_qubits
        self.max_bond = int(max_bond)
        self.cutoff = float(cutoff)
        if tree_mode not in {"weighted", "unweighted"}:
            raise ValueError("tree_mode must be weighted or unweighted")
        self.tree_mode = tree_mode
        self.tree = build_weighted_tree(circuit) if tree_mode == "weighted" else build_unweighted_tree(circuit)
        self.nodes, self.parent, self.leaf_node, self.children = _tree_index(self.tree)
        self.tensors: dict[int, np.ndarray] = {}
        self.edge_id: dict[tuple[int, int], int] = {}
        edge_count = 0
        for node_id, child_ids in self.children.items():
            for child_id in child_ids:
                self.edge_id[(node_id, child_id)] = edge_count
                edge_count += 1
        self._initialize_product_zero()
        self.gates_applied = 0
        self.truncation_events = 0
        self.discarded_weight_proxy = 0.0

    def _initialize_product_zero(self) -> None:
        for node_id, child_ids in self.children.items():
            if not child_ids:
                tensor = np.zeros((2, 1), dtype=np.complex128)
                tensor[0, 0] = 1.0
            else:
                shape = [1] * len(child_ids) + ([1] if node_id in self.parent else [])
                tensor = np.ones(shape, dtype=np.complex128)
            self.tensors[node_id] = tensor

    def _edge_between(self, left: int, right: int) -> int:
        if self.parent.get(left) == right:
            return self.edge_id[(right, left)]
        if self.parent.get(right) == left:
            return self.edge_id[(left, right)]
        raise ValueError("nodes are not adjacent")

    def _path(self, leaf_a: int, leaf_b: int) -> list[int]:
        a = self.leaf_node[leaf_a]
        b = self.leaf_node[leaf_b]
        a_chain = [a]
        b_chain = [b]
        while a_chain[-1] in self.parent:
            a_chain.append(self.parent[a_chain[-1]])
        while b_chain[-1] in self.parent:
            b_chain.append(self.parent[b_chain[-1]])
        b_positions = {node: index for index, node in enumerate(b_chain)}
        lca_index_a = next(index for index, node in enumerate(a_chain) if node in b_positions)
        lca_index_b = b_positions[a_chain[lca_index_a]]
        return a_chain[: lca_index_a + 1] + list(reversed(b_chain[:lca_index_b]))

    def apply_one_qubit(self, qubit: int, matrix: np.ndarray) -> None:
        node = self.leaf_node[qubit]
        tensor = self.tensors[node]
        self.tensors[node] = np.tensordot(np.asarray(matrix, dtype=np.complex128), tensor, axes=([1], [0]))
        self.gates_applied += 1

    def apply_two_qubit(self, qubit_a: int, qubit_b: int, matrix: np.ndarray) -> None:
        path = self._path(qubit_a, qubit_b)
        if path[0] != self.leaf_node[qubit_a] or path[-1] != self.leaf_node[qubit_b]:
            raise ValueError("path orientation does not match gate endpoints")
        effective, local_labels, local_shapes = self._contract_path(path, qubit_a, qubit_b)
        gate = np.asarray(matrix, dtype=np.complex128).reshape(2, 2, 2, 2)
        last_axis = effective.ndim - 1
        updated = np.tensordot(gate, effective, axes=([2, 3], [0, last_axis]))
        remaining = list(range(2, updated.ndim))
        updated = np.transpose(updated, [0] + remaining + [1])
        self._split_path(path, local_labels, local_shapes, updated)
        self.gates_applied += 1

    def _canonical_labels(self, node_id: int, physical_label: int | None = None) -> list[int]:
        labels: list[int] = []
        if physical_label is not None:
            labels.append(physical_label)
        child_ids = self.children[node_id]
        labels.extend(self.edge_id[(node_id, child_id)] for child_id in child_ids)
        if node_id in self.parent:
            labels.append(self.edge_id[(self.parent[node_id], node_id)])
        return labels

    def _contract_path(self, path: list[int], qubit_a: int, qubit_b: int) -> tuple[np.ndarray, list[list[int]], list[list[int]]]:
        path_set = set(path)
        operands: list[object] = []
        output_labels: list[int] = []
        local_labels: list[list[int]] = []
        local_shapes: list[list[int]] = []
        next_label = max(self.edge_id.values(), default=-1) + 1
        for position, node_id in enumerate(path):
            physical = None
            if not self.children[node_id]:
                physical = next_label
                next_label += 1
            labels = self._canonical_labels(node_id, physical)
            tensor = self.tensors[node_id]
            path_edge_labels = set()
            if position:
                path_edge_labels.add(self._edge_between(path[position - 1], node_id))
            if position + 1 < len(path):
                path_edge_labels.add(self._edge_between(node_id, path[position + 1]))
            local = [label for label in labels if label not in path_edge_labels]
            local_labels.append(local)
            shape_by_label = dict(zip(labels, tensor.shape))
            local_shapes.append([shape_by_label[label] for label in local])
            operands.extend([tensor, labels])
            output_labels.extend(local)
        # ``numpy.einsum`` has a small alphabet limit for integer labels.
        # Relabel this local contraction densely; retain the original labels
        # for reconstructing the tree tensors after the SVD.
        labels_in_order = []
        for item in operands[1::2]:
            labels_in_order.extend(item)
        labels_in_order.extend(output_labels)
        relabel = {label: index for index, label in enumerate(dict.fromkeys(labels_in_order))}
        compact_operands: list[object] = []
        for index in range(0, len(operands), 2):
            compact_operands.extend([operands[index], [relabel[label] for label in operands[index + 1]]])
        compact_operands.append([relabel[label] for label in output_labels])
        result = np.einsum(*compact_operands, optimize=True)
        return result, local_labels, local_shapes

    def _split_path(self, path: list[int], local_labels: list[list[int]], local_shapes: list[list[int]], effective: np.ndarray) -> None:
        local_dims = [max(1, int(np.prod(shape, dtype=int))) for shape in local_shapes]
        current = effective.reshape(local_dims)
        factors: list[np.ndarray] = []
        left_dim = 1
        for index in range(len(path) - 1):
            matrix = current.reshape(left_dim * local_dims[index], -1)
            u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
            keep = min(self.max_bond, len(singular))
            if singular.size:
                keep = min(keep, max(1, int(np.count_nonzero(singular > self.cutoff * singular[0]))))
                discarded = singular[keep:]
                self.discarded_weight_proxy += float(np.sum(np.abs(discarded) ** 2))
                if len(discarded):
                    self.truncation_events += 1
            u = u[:, :keep]
            singular = singular[:keep]
            vh = vh[:keep, :]
            factors.append(u.reshape(left_dim, *local_shapes[index], keep))
            current = singular[:, None] * vh
            left_dim = keep
        factors.append(current.reshape(left_dim, *local_shapes[-1]))
        for index, node_id in enumerate(path):
            prev_edge = self._edge_between(path[index - 1], node_id) if index else None
            next_edge = self._edge_between(node_id, path[index + 1]) if index + 1 < len(path) else None
            # The physical labels are the first and last local labels, and are
            # not present for internal path nodes. Rebuild desired axes by label.
            local = local_labels[index]
            physical = local[0] if not self.children[node_id] and local else None
            canonical = self._canonical_labels(node_id, physical)
            factor = factors[index]
            # The first chain factor has a dummy left bond of dimension one;
            # remove it because the endpoint leaf has no incoming tree edge.
            if index == 0:
                factor = factor[0]
                local_offset = 0
            else:
                local_offset = 1
            axis_for_label = {label: local_offset + offset for offset, label in enumerate(local)}
            axis_for_label[prev_edge] = 0 if prev_edge is not None else None
            axis_for_label[next_edge] = factor.ndim - 1 if next_edge is not None else None
            desired: list[int] = []
            for label in canonical:
                axis = axis_for_label.get(label)
                if axis is None:
                    raise RuntimeError("TTN path factorization lost a canonical axis")
                desired.append(axis)
            self.tensors[node_id] = np.transpose(factor, desired)

    def _message(self, node_id: int, assignment: dict[int, int]) -> np.ndarray:
        child_ids = self.children[node_id]
        tensor = self.tensors[node_id]
        if not child_ids:
            bit = assignment.get(self.nodes[node_id].leaves[0])
            if bit is None:
                return np.einsum("pb,qb->pq", tensor, np.conjugate(tensor), optimize=True)
            vector = tensor[int(bit)]
            return np.outer(vector, np.conjugate(vector))
        messages = [self._message(child_id, assignment) for child_id in child_ids]
        if node_id in self.parent:
            if len(child_ids) != 2:
                raise ValueError("only binary internal nodes are supported")
            return np.einsum("abp,cdq,ac,bd->pq", tensor, np.conjugate(tensor), messages[0], messages[1], optimize=True)
        if len(child_ids) != 2:
            raise ValueError("only binary roots are supported")
        return np.einsum("ab,cd,ac,bd->", tensor, np.conjugate(tensor), messages[0], messages[1], optimize=True).reshape(1, 1)

    def mass(self, assignment: dict[int, int] | None = None) -> float:
        message = self._message(0, assignment or {})
        return max(0.0, float(np.real(message[0, 0])))

    def marginal_factors(self, edges: Iterable[tuple[int, int]]) -> tuple[np.ndarray, dict[tuple[int, int], np.ndarray], float]:
        """Return positive unary and pairwise marginals of the approximate TTN.

        These are exact marginals of the *truncated TTN state* (not of the
        target circuit). They are suitable as an answer-blind diagnostic input
        to a graph decoder and are intentionally kept separate from candidate
        promotion.
        """
        total = self.mass({})
        if total <= 0 or not np.isfinite(total):
            raise ValueError("TTN has non-positive total mass")
        unary = np.empty((self.n_qubits, 2), dtype=float)
        for qubit in range(self.n_qubits):
            unary[qubit] = [self.mass({qubit: bit}) / total for bit in (0, 1)]
        pairwise: dict[tuple[int, int], np.ndarray] = {}
        for left, right in edges:
            if left == right or not (0 <= left < self.n_qubits and 0 <= right < self.n_qubits):
                raise ValueError("invalid marginal edge")
            matrix = np.asarray([[self.mass({left: a, right: b}) / total for b in (0, 1)] for a in (0, 1)], dtype=float)
            pairwise[(min(left, right), max(left, right))] = matrix if left < right else matrix.T
        return unary, pairwise, total

    def decode(self, *, beam_width: int = 64, order: Iterable[int] | None = None) -> TTNDecode:
        if beam_width < 1:
            raise ValueError("beam_width must be positive")
        leaves = list(order or sorted(self.leaf_node))
        beam: list[tuple[float, dict[int, int]]] = [(self.mass({}), {})]
        expanded = 0
        for qubit in leaves:
            candidates: list[tuple[float, dict[int, int]]] = []
            for _, assignment in beam:
                for bit in (0, 1):
                    child = dict(assignment)
                    child[qubit] = bit
                    candidates.append((self.mass(child), child))
                    expanded += 1
            candidates.sort(key=lambda item: (-item[0], tuple(item[1][q] for q in leaves if q in item[1])))
            beam = candidates[:beam_width]
        total = self.mass({})
        best_mass, best_assignment = beam[0]
        bitstring = "".join(str(best_assignment[q]) for q in sorted(self.leaf_node))
        return TTNDecode(bitstring, best_mass / total if total else 0.0, total, beam_width, expanded)


def simulate_ttn(circuit: PeakQASM, *, max_bond: int = 4, cutoff: float = 1e-10, tree_mode: str = "weighted") -> TreeTensorState:
    state = TreeTensorState(circuit, max_bond=max_bond, cutoff=cutoff, tree_mode=tree_mode)
    return state
