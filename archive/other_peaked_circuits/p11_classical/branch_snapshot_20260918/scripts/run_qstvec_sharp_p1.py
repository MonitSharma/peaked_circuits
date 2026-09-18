#!/usr/bin/env python3
"""Run the pinned public qstvec sharp-peak block strategy on blind P1."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.quantum_info import ScalarOp
from qiskit.transpiler.passes import RemoveBarriers


def build_blocks(qc: QuantumCircuit):
    dag = circuit_to_dag(qc)
    blocks, all_qubits, block_qubits = [], set(), set()
    def qset(node):
        return {dag.find_bit(q).index for q in node.qargs}
    def key(node):
        current = qset(node)
        return (len(all_qubits | current) - len(all_qubits), len(block_qubits | current) - len(block_qubits), tuple(sorted(current)))
    while dag.size() > 0:
        node = min(dag.front_layer(), key=key)
        current = qset(node)
        dag.remove_op_node(node)
        if not blocks:
            blocks.append([node]); block_qubits = current; all_qubits = current; continue
        if current.issubset(block_qubits):
            blocks[-1].append(node); continue
        if len(current | block_qubits) <= 2:
            blocks[-1].append(node); block_qubits |= current; all_qubits |= current; continue
        blocks.append([node]); block_qubits = current; all_qubits |= current
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--p-frac", type=float, default=1.0)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    args = parser.parse_args()
    sys.path.insert(0, str(Path("external/qstvec/src").resolve()))
    from qstvec import Statevector
    qc = RemoveBarriers()(QuantumCircuit.from_qasm_file(str(args.qasm)))
    qc.remove_final_measurements()
    blocks = build_blocks(qc)
    state = Statevector(qc.num_qubits)
    started = time.monotonic()
    progress = []
    completed_blocks = 0
    aborted = None
    for block_index, block in enumerate(blocks):
        qargs = sorted({qc.find_bit(q).index for node in block for q in node.qargs})
        unitary = ScalarOp(2 ** len(qargs), coeff=1.0 + 0.0j)
        for node in block:
            local = [qargs.index(qc.find_bit(q).index) for q in node.qargs]
            unitary = unitary.compose(node.op, qargs=local)
        state.evolve(unitary.data, qargs)
        state.truncate(args.top_k, args.p_frac)
        completed_blocks = block_index + 1
        if block_index % 25 == 0 or block_index == len(blocks) - 1:
            bit, prob = state.bit_string(return_prob=True)
            progress.append({"block": block_index, "event_count": sum(len(item) for item in blocks[:block_index + 1]), "support": len(state), "top1": bit, "top1_probability_renormalized": float(prob)})
        if time.monotonic() - started >= args.max_seconds:
            aborted = "wall_time_abort"
            break
    bit, prob = state.bit_string(return_prob=True)
    result = {"schema": "bluequbit-p1-v2-qstvec-sharp-run-v1", "blind": True, "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(), "configuration": {"top_k": args.top_k, "p_frac": args.p_frac, "max_seconds": args.max_seconds, "strategy": "public_qstvec_sharp_peak_exact_block_builder"}, "block_count": len(blocks), "progress": {"blocks_completed": completed_blocks, "blocks_total": len(blocks), "aborted": aborted}, "runtime_s": time.monotonic() - started, "final_support": len(state), "top1": bit, "top1_probability_renormalized": float(prob), "trace": progress, "decision": "INCONCLUSIVE_UNLESS_REPEATED_ACROSS_K"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
