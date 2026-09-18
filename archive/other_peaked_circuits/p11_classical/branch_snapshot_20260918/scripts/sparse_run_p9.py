#!/usr/bin/env python3
"""Run one bounded, sequential P9 sparse method at one fixed top-k budget."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "external/qstvec/src"))
sys.path.insert(0, str(ROOT / "external/bass"))

import numpy as np
from qiskit import QuantumCircuit

from p12_recovery.sparse_campaign.common_metrics import (
    artifact_hashes,
    participation_ratio,
    sparse_target_metrics,
    target_probability_in_product_frame,
    write_json,
)
from p12_recovery.sparse_campaign.provenance import environment, file_sha256, git_info
from p12_recovery.sparse_campaign.qasm_adapter import parse_qasm


P9_TARGET = "01101110111001100000100000001010011100101101010111110111"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("qstvec", "bass_fixed", "bass_adaptive"), required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--qasm", type=Path, default=ROOT / "data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm")
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    parser.add_argument("--optimize-every", type=int, default=5)
    return parser.parse_args()


def _qstvec_run(stream, k, started):
    from qstvec import Statevector
    state = Statevector(stream.n_qubits)
    nnz = [1]
    for gate in stream.gates:
        state.evolve(gate.qstvec_matrix(), gate.qubits).truncate(top_k=k)
        nnz.append(len(state))
    indices = np.asarray(state.basis)
    amplitudes = np.asarray(state.alpha)
    position = np.flatnonzero(indices == int(P9_TARGET, 2))
    order = np.argsort(np.abs(amplitudes) ** 2)[::-1]
    target_rank = int(np.flatnonzero(indices[order] == int(P9_TARGET, 2))[0] + 1) if len(position) else None
    top_index = int(indices[order[0]])
    return {
        "metrics": {
            "top1_bitstring": f"{top_index:0{stream.n_qubits}b}",
            "top1_hamming_to_p9": sum(a != b for a, b in zip(f"{top_index:0{stream.n_qubits}b}", P9_TARGET)),
            "target_present": bool(len(position)),
            "target_rank": target_rank,
            "target_weight": float(abs(amplitudes[position[0]]) ** 2) if len(position) else 0.0,
            "final_nnz": int(len(state)),
            "final_participation_ratio": participation_ratio(amplitudes),
        },
        "trajectory": {"nnz": nnz},
    }


def _bass_run(stream, k, method, seed, optimize_every):
    from src.simulation.bass_simulator import BASS
    from src.simulation.simulator import FixedBasisSimulator

    gates = [
        type(gate)(gate.name, gate.qubits, gate.bass_matrix(), gate.original_params, gate.instruction_index)
        for gate in stream.gates
    ]
    if method == "bass_fixed":
        simulator = FixedBasisSimulator(stream.n_qubits, k, verbose=False)
        state = simulator.simulate(gates, seed=seed)
        metrics = sparse_target_metrics(state, stream.n_qubits, P9_TARGET)
        metrics["final_participation_ratio"] = participation_ratio(state.alpha[: state.nnz])
        metrics["gamma_squared"] = float(state.gamma**2)
        trajectory = {
            "nnz": simulator.nnz_history.tolist(),
            "gamma_squared": (simulator.gamma_history**2).tolist(),
        }
    else:
        simulator = BASS(
            stream.n_qubits,
            k,
            optimize_every=optimize_every,
            truncate_every=1,
            use_2qubit_rotations=False,
            verbose=False,
        )
        state = simulator.simulate(gates)
        target_probability = target_probability_in_product_frame(
            state, simulator.U, stream.n_qubits, P9_TARGET
        )
        metrics = {
            "top1_bitstring": None,
            "top1_hamming_to_p9": None,
            "target_present": None,
            "target_rank": None,
            "target_weight": target_probability,
            "final_nnz": int(state.nnz),
            "final_participation_ratio": participation_ratio(state.alpha[: state.nnz]),
            "gamma_squared": float(state.gamma**2),
            "computational_basis_endpoint": "single_target_amplitude_only",
        }
        trajectory = {
            "nnz": [int(state.nnz)],
            "gamma_squared": [float(state.gamma**2)],
            "adaptive_basis_transforms": len(simulator.U),
        }
    return {"metrics": metrics, "trajectory": trajectory}


def main():
    args = parse_args()
    if args.k < 1:
        raise SystemExit("k must be positive")
    qasm = args.qasm.resolve()
    canonical = parse_qasm(qasm)
    started = time.perf_counter()
    previous_handler = None
    if args.max_seconds is not None and hasattr(signal, "SIGALRM"):
        previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("P9 sparse run wall-time limit exceeded")))
        signal.setitimer(signal.ITIMER_REAL, args.max_seconds)
    try:
        if args.method == "qstvec":
            result = _qstvec_run(canonical, args.k, started)
        else:
            result = _bass_run(canonical, args.k, args.method, args.seed, args.optimize_every)
        termination_reason = "completed"
    except TimeoutError as exc:
        result = {"metrics": {}, "trajectory": {}}
        termination_reason = str(exc)
    finally:
        if args.max_seconds is not None and hasattr(signal, "SIGALRM"):
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    elapsed = time.perf_counter() - started
    output = {
        "schema": "p11-sparse-p9-run-v1",
        "method": args.method,
        "k": args.k,
        "qasm": str(qasm),
        "qasm_sha256": file_sha256(qasm),
        "canonical_gate_stream_sha256": canonical.canonical_sha256,
        "n_qubits": canonical.n_qubits,
        "gate_count": len(canonical.gates),
        "measurement_permutation": list(canonical.measurement_permutation),
        "p9_target_supervised_calibration": True,
        "p9_target_sha256": file_sha256_bytes(P9_TARGET.encode()),
        "seed": args.seed,
        "parameters": {"optimize_every": args.optimize_every},
        "runtime_s": elapsed,
        "termination_reason": termination_reason,
        "environment": environment(),
        "repository": git_info(ROOT),
        "qstvec": git_info(ROOT / "external/qstvec"),
        "bass": git_info(ROOT / "external/bass"),
        **result,
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_json(args.outdir / "summary.json", output)
    write_json(args.outdir / "artifact_hashes.json", artifact_hashes(args.outdir))
    print(json.dumps(output, indent=2))


def file_sha256_bytes(value: bytes) -> str:
    import hashlib
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    main()
