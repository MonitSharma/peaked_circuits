"""CPU tensor-network-operator attack adapted from the public peaked-circuit method.

This module intentionally keeps the public method's mirrored TNO idea separate
from the existing MPS/MPO solver. It uses numpy-backed Quimb tensors and a
bounded greedy contraction path, which is safer on a Mac than a hyperoptimizer.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit_quimb import quimb_circuit
from quimb.tensor import Circuit, MatrixProductOperator
from quimb.tensor.tensor_arbgeom_compress import tensor_network_ag_compress


def iter_layers(qc: QuantumCircuit):
    for layer in circuit_to_dag(qc).layers():
        yield dag_to_circuit(layer["graph"])


def _identity_circuit(n_qubits: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits)
    qc.x(range(n_qubits))
    qc.x(range(n_qubits))
    return qc


def _to_quimb(qc: QuantumCircuit):
    return quimb_circuit(qc, Circuit, to_backend=None)


def _operator_from_circuit(qc: QuantumCircuit) -> MatrixProductOperator:
    circ = _to_quimb(qc)
    for tag in list(circ.site_tags):
        circ ^= tag
    circ.fuse_multibonds_()
    mpo = circ.view_as(MatrixProductOperator, cyclic=False, L=qc.num_qubits)
    mpo.ensure_bonds_exist()
    return mpo


def _compress(tn, *, max_bond: int, cutoff: float, method: str, optimize: str):
    return tensor_network_ag_compress(
        tn,
        method=method,
        cutoff=cutoff,
        max_bond=max_bond,
        site_tags=tn.site_tags,
        canonize=True,
        equalize_norms=True,
        optimize=optimize,
    ).squeeze()


def contract_core(
    layers: list[QuantumCircuit],
    *,
    chunk_size: int = 4,
    method: str = "local-late",
    max_bond: int = 16,
    cutoff: float = 0.1,
    optimize: str = "greedy",
    max_seconds: float = 120.0,
) -> tuple[Any, list[dict[str, Any]], bool]:
    """Contract a bounded center TNO from both circuit sides."""
    if not layers:
        raise ValueError("at least one layer is required")
    n_qubits = layers[0].num_qubits
    midpoint = len(layers) // 2
    identity = _identity_circuit(n_qubits)
    core = _to_quimb(layers[midpoint].compose(identity)).get_uni()
    left = layers[:midpoint][::-1]
    right = layers[midpoint + 1 :]
    started = time.monotonic()
    stats: list[dict[str, Any]] = []
    for distance in range(0, max(midpoint, len(right)) + 1, chunk_size):
        if time.monotonic() - started >= max_seconds:
            return core, stats, True
        left_chunk = identity.copy()
        for layer in reversed(left[distance : distance + chunk_size]):
            left_chunk = left_chunk.compose(layer)
        right_chunk = identity.copy()
        for layer in right[distance : distance + chunk_size]:
            right_chunk = right_chunk.compose(layer)
        core = core.gate_upper_with_op_lazy(_to_quimb(left_chunk).get_uni())
        core = core.gate_upper_with_op_lazy(_to_quimb(right_chunk).get_uni())
        core = _compress(core, max_bond=max_bond, cutoff=cutoff, method=method, optimize=optimize)
        stats.append({"distance": distance, "max_bond": int(core.max_bond() or 1), "num_tensors": int(core.num_tensors), "elapsed_s": time.monotonic() - started})
    return core, stats, False


def finish_state(core, *, max_bond: int, cutoff: float, method: str = "local-late", optimize: str = "greedy") -> Any:
    """Apply the TNO to |0...0> and compress to a state tensor network."""
    state = _to_quimb(QuantumCircuit(len(core.sites))).psi
    state = core.apply(state, compress=False)
    return _compress(state, max_bond=max_bond, cutoff=cutoff, method=method, optimize=optimize)


def product_marginal_bitstring(state) -> tuple[str, list[float]]:
    """Return the computational-basis product-marginal decoder."""
    p0s: list[float] = []
    for site in state.sites:
        p0 = state.local_expectation(np.array([[1.0, 0.0], [0.0, 0.0]]), where=[site], max_bond=2, normalized=True, optimize="greedy").real.item()
        p0s.append(float(p0))
    return "".join("0" if p0 >= 0.5 else "1" for p0 in p0s), p0s
