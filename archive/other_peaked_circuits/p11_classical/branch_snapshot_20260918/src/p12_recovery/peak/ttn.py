"""Geometry-aware tree planning and small exact TTN controls.

The tree planner is production-safe metadata: it uses only the interaction graph.
The exact state helper is deliberately limited to small controls and is never
used as a target-circuit simulator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .qasm import PeakQASM


@dataclass(frozen=True)
class TreeNode:
    leaves: tuple[int, ...]
    children: tuple["TreeNode", ...] = ()
    cut_weight: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "leaves": list(self.leaves),
            "cut_weight": self.cut_weight,
            "children": [child.as_dict() for child in self.children],
        }


def _weights(circuit: PeakQASM) -> dict[tuple[int, int], float]:
    result: dict[tuple[int, int], float] = {}
    for gate in circuit.gates:
        if len(gate.qubits) == 2:
            edge = tuple(sorted(gate.qubits))
            result[edge] = result.get(edge, 0.0) + 1.0
    return result


def _spectral_split(leaves: tuple[int, ...], weights: dict[tuple[int, int], float]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if len(leaves) < 2:
        raise ValueError("cannot split a singleton")
    index = {leaf: i for i, leaf in enumerate(leaves)}
    laplacian = np.zeros((len(leaves), len(leaves)), dtype=float)
    for (left, right), weight in weights.items():
        if left not in index or right not in index:
            continue
        i, j = index[left], index[right]
        laplacian[i, i] += weight
        laplacian[j, j] += weight
        laplacian[i, j] -= weight
        laplacian[j, i] -= weight
    values, vectors = np.linalg.eigh(laplacian)
    fiedler = vectors[:, 1] if len(leaves) > 2 else np.arange(len(leaves), dtype=float)
    order = sorted(range(len(leaves)), key=lambda i: (float(fiedler[i]), leaves[i]))
    midpoint = max(1, len(order) // 2)
    if midpoint == len(order):
        midpoint -= 1
    return tuple(sorted(leaves[i] for i in order[:midpoint])), tuple(sorted(leaves[i] for i in order[midpoint:]))


def _cut_weight(left: tuple[int, ...], right: tuple[int, ...], weights: dict[tuple[int, int], float]) -> float:
    left_set, right_set = set(left), set(right)
    return float(sum(weight for (a, b), weight in weights.items() if (a in left_set and b in right_set) or (a in right_set and b in left_set)))


def _build_tree(circuit: PeakQASM, weights: dict[tuple[int, int], float]) -> TreeNode:
    def build(leaves: tuple[int, ...]) -> TreeNode:
        if len(leaves) == 1:
            return TreeNode(leaves)
        left, right = _spectral_split(leaves, weights)
        return TreeNode(leaves, (build(left), build(right)), _cut_weight(left, right, weights))

    return build(tuple(range(circuit.n_qubits)))


def build_weighted_tree(circuit: PeakQASM) -> TreeNode:
    """Build a balanced recursive spectral tree from weighted interactions."""
    return _build_tree(circuit, _weights(circuit))


def build_unweighted_tree(circuit: PeakQASM) -> TreeNode:
    """Build the same spectral tree using edge presence, not multiplicity."""
    weights = {edge: 1.0 for edge in _weights(circuit)}
    return _build_tree(circuit, weights)


def tree_leaves(tree: TreeNode) -> tuple[int, ...]:
    if not tree.children:
        return tree.leaves
    return tuple(leaf for child in tree.children for leaf in tree_leaves(child))


def cut_rank_profile(statevector: np.ndarray, tree: TreeNode, *, tolerance: float = 1e-10) -> list[dict[str, Any]]:
    """Measure exact Schmidt ranks across tree node/complement cuts for controls."""
    vector = np.asarray(statevector, dtype=np.complex128)
    n = int(round(np.log2(vector.size)))
    if vector.size != 2**n or set(tree_leaves(tree)) != set(range(n)):
        raise ValueError("statevector and tree must describe the same qubits")
    tensor = vector.reshape([2] * n)
    rows: list[dict[str, Any]] = []

    def visit(node: TreeNode) -> None:
        leaves = tuple(sorted(node.leaves))
        if len(leaves) < n:
            rest = tuple(i for i in range(n) if i not in leaves)
            matrix = np.transpose(tensor, leaves + rest).reshape(2 ** len(leaves), 2 ** len(rest))
            singular = np.linalg.svd(matrix, compute_uv=False)
            scale = float(singular[0]) if len(singular) else 0.0
            rank = int(np.sum(singular > tolerance * max(scale, 1.0)))
            rows.append({"leaves": list(leaves), "rank": rank, "largest_singular": scale, "cut_weight": node.cut_weight})
        for child in node.children:
            visit(child)

    visit(tree)
    return rows


def exact_tree_topk(statevector: np.ndarray, *, k: int = 32) -> list[dict[str, Any]]:
    """Exact small-control decoder; callers must label it control-only."""
    vector = np.asarray(statevector, dtype=np.complex128)
    n = int(round(np.log2(vector.size)))
    if vector.size != 2**n or n > 20:
        raise ValueError("exact tree controls are limited to at most 20 qubits")
    probabilities = np.abs(vector) ** 2
    indices = np.argsort(-probabilities, kind="stable")[:k]
    return [{"bitstring": format(int(index), f"0{n}b"), "probability": float(probabilities[index])} for index in indices]
