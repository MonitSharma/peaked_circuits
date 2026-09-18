#!/usr/bin/env python3
"""Bounded, answer-blind public-style TNO screen for P5/P6/P9."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qiskit import QuantumCircuit  # noqa: E402
from p12_recovery.bluequbit.tno import contract_core, finish_state  # noqa: E402


def run(path: Path, args: argparse.Namespace) -> dict:
    started = time.monotonic()
    qc = QuantumCircuit.from_qasm_file(str(path))
    qc.remove_final_measurements()
    if args.twoq_prefix is not None:
        prefix = QuantumCircuit(qc.num_qubits)
        seen = 0
        for instruction in qc.data:
            qargs = [prefix.qubits[qc.find_bit(qubit).index] for qubit in instruction.qubits]
            cargs = [prefix.clbits[qc.find_bit(clbit).index] for clbit in instruction.clbits]
            prefix.append(instruction.operation, qargs, cargs)
            if len(instruction.qubits) == 2:
                seen += 1
                if seen >= args.twoq_prefix:
                    break
        qc = prefix
    # Avoid target-dependent decoders in this screen.  Core telemetry is the
    # relevant representation test; state finishing is optional and bounded.
    from p12_recovery.bluequbit.tno import iter_layers
    layers = list(iter_layers(qc))
    result = {
        "schema": "p6-public-tno-screen-v1",
        "answer_blind": True,
        "source": str(path.resolve()),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "qubits": qc.num_qubits,
        "layers": len(layers),
        "twoq_prefix": args.twoq_prefix,
        "configuration": {
            "max_bond": args.max_bond,
            "cutoff": args.cutoff,
            "chunk_size": args.chunk_size,
            "max_seconds": args.max_seconds,
            "method": args.method,
            "optimize": args.optimize,
        },
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }
    try:
        core, trace, timed_out = contract_core(
            layers,
            chunk_size=args.chunk_size,
            method=args.method,
            max_bond=args.max_bond,
            cutoff=args.cutoff,
            optimize=args.optimize,
            max_seconds=args.max_seconds,
        )
        result.update({"status": "CORE_TIMEOUT" if timed_out else "CORE_COMPLETE", "trace": trace})
        if not timed_out and args.finish_state:
            state_started = time.monotonic()
            state = finish_state(core, max_bond=args.state_max_bond, cutoff=args.state_cutoff)
            result["state_finish"] = {
                "status": "complete",
                "elapsed_s": time.monotonic() - state_started,
                "max_bond": int(state.max_bond() or 1),
                "num_tensors": int(state.num_tensors),
            }
    except Exception as exc:
        result.update({"status": "EXCEPTION", "error_type": type(exc).__name__, "error": str(exc)})
    result["runtime_s"] = time.monotonic() - started
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qasm", nargs="+", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-bond", type=int, default=16)
    ap.add_argument("--cutoff", type=float, default=0.01)
    ap.add_argument("--chunk-size", type=int, default=4)
    ap.add_argument("--max-seconds", type=float, default=120.0)
    ap.add_argument("--method", default="local-late")
    ap.add_argument("--optimize", default="greedy")
    ap.add_argument("--finish-state", action="store_true")
    ap.add_argument("--state-max-bond", type=int, default=8)
    ap.add_argument("--state-cutoff", type=float, default=0.01)
    ap.add_argument("--twoq-prefix", type=int, default=None,
                    help="Truncate each input after this many two-qubit events.")
    args = ap.parse_args()
    payload = {"schema": "p6-public-tno-screen-v1", "answer_blind": True, "runs": [run(path, args) for path in args.qasm]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
