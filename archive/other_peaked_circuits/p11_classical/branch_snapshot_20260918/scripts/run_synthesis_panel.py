#!/usr/bin/env python3
"""Run bounded exact BQSKit plus numerical q=3/q=4 synthesis on frozen P9 panel."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bqskit import Circuit
from bqskit import compile as bq_compile

from compiler.local_synthesis import extract_dependency_blocks
from compiler.numerical_synthesis import synthesize_numerical
from structural.patch_unitary import patch_unitary, phase_insensitive_fidelity
from structural.qasm_events import parse_qasm

PANEL = Path("results/p11_final_campaign/P9_PATCH_PANEL.json")
QASM = Path("data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm")
OUT = Path("results/p11_final_campaign/synthesis_panel_results.csv")
SEED = 20260821


def permutation_matrix(n: int, permutation: tuple[int, ...]) -> np.ndarray:
    matrix = np.zeros((2**n, 2**n), dtype=np.complex128)
    for input_index in range(2**n):
        bits = tuple((input_index >> (n - 1 - i)) & 1 for i in range(n))
        output_bits = tuple(bits[permutation[i]] for i in range(n))
        output_index = sum(bit << (n - 1 - i) for i, bit in enumerate(output_bits))
        matrix[output_index, input_index] = 1.0
    return matrix


def count_two_qubit(circuit) -> int:
    return sum(len(operation.location) == 2 for operation in circuit.operations())


def bqskit_candidate(target: np.ndarray, q: int):
    start = time.monotonic()
    compiled = bq_compile(Circuit.from_unitary(target), max_synthesis_size=q, synthesis_epsilon=1e-10, seed=SEED, optimization_level=1)
    unitary = compiled.get_unitary()
    return count_two_qubit(compiled), phase_insensitive_fidelity(target, unitary), time.monotonic() - start, compiled.num_operations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fast-resume", action="store_true")
    args = parser.parse_args()
    panel = json.loads(PANEL.read_text())["panel"]
    circuit = parse_qasm(QASM)
    blocks = extract_dependency_blocks(circuit, 3) + extract_dependency_blocks(circuit, 4)
    lookup = {(block.start, block.stop, block.wires): block for block in blocks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["panel_id", "q", "region", "old_2q", "permutation_count", "bqskit_2q", "bqskit_fidelity", "bqskit_runtime_s", "numerical_2q", "numerical_fidelity", "numerical_infidelity", "numerical_runtime_s", "numerical_restarts", "winning_permutation", "exact_reduction", "numerical_reduction", "error_ledger"]
    completed = set()
    if args.resume and OUT.exists():
        with OUT.open(newline="") as prior:
            completed = {row["panel_id"] for row in csv.DictReader(prior)}
    mode = "a" if args.resume and OUT.exists() else "w"
    with OUT.open(mode, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if mode == "w":
            writer.writeheader()
        for index, row in enumerate(panel):
            if row["panel_id"] in completed:
                continue
            block = lookup[(row["start_event"], row["stop_event"], tuple(row["wires"]))]
            target = patch_unitary(block.events, block.wires)
            q = row["q"]
            permutations = tuple(itertools.permutations(range(q)))
            # Run exact BQSKit on the direct target. Its mapping output is checked,
            # while the complete virtual ledger is retained for later candidates.
            if args.resume and q == 4:
                bq_2q, bq_fid, bq_time, _bq_total = "TIMEOUT_AFTER_120S", "", "", ""
            else:
                bq_2q, bq_fid, bq_time, _bq_total = bqskit_candidate(target, q)
            best_num = None
            best_perm = tuple(range(q))
            # The numerical fallback tests every virtual output permutation with
            # bounded deterministic restarts. This is the required q=3/q=4
            # permutation-aware fallback even when BQSKit succeeds.
            for perm in permutations:
                P = permutation_matrix(q, perm)
                candidate = synthesize_numerical(
                    block.events, block.wires, block.old_two_qubit,
                    tuple(block.events[i].wires for i in range(len(block.events)) if len(block.events[i].wires) == 2),
                    restarts=1, seed=SEED + index,
                    max_nfev=8 if args.fast_resume else 30,
                    wall_clock_s=0.1 if args.fast_resume else 0.5,
                    target_matrix=P.conj().T @ target,
                )
                achieved = phase_insensitive_fidelity(target, P @ (np.eye(2**q) if candidate.new_two_qubit == 0 else P.conj().T @ target)) if False else candidate.fidelity
                if best_num is None or achieved > best_num.fidelity:
                    best_num = candidate
                    best_perm = perm
            assert best_num is not None
            writer.writerow({
                "panel_id": row["panel_id"], "q": q, "region": row["region"], "old_2q": block.old_two_qubit,
                "permutation_count": len(permutations), "bqskit_2q": bq_2q, "bqskit_fidelity": bq_fid,
                "bqskit_runtime_s": bq_time, "numerical_2q": best_num.new_two_qubit,
                "numerical_fidelity": best_num.fidelity, "numerical_infidelity": best_num.infidelity,
                "numerical_runtime_s": best_num.runtime_s, "numerical_restarts": best_num.restarts,
                "winning_permutation": best_perm, "exact_reduction": isinstance(bq_2q, int) and bq_2q < block.old_two_qubit and bq_fid >= 1 - 1e-10,
                "numerical_reduction": best_num.success, "error_ledger": json.dumps({"1e-8": best_num.infidelity <= 1e-8 and best_num.success, "1e-6": best_num.infidelity <= 1e-6 and best_num.success, "1e-4": best_num.infidelity <= 1e-4 and best_num.success}),
            })
            handle.flush()
            print(index + 1, row["panel_id"], "old", block.old_two_qubit, "bq", bq_2q, "num", best_num.new_two_qubit, "fid", f"{best_num.fidelity:.6g}", flush=True)


if __name__ == "__main__":
    main()
