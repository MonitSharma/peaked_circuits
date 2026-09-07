#!/usr/bin/env python3
"""Prepare an offline, two-qubit-optimized P6 candidate circuit.

This script performs no provider calls and submits no jobs.  It records the
source/output hashes and basic gate counts so the generated circuit can be
costed and reviewed before any hardware use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pytket.circuit import OpType
from pytket.passes import DecomposeTK2, FullPeepholeOptimise, NormaliseTK2
from pytket.qasm import circuit_from_qasm_str, circuit_to_qasm_str


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "results/hardware/p6_helios_50shot_20260829/source.qasm"
DEFAULT_OUTPUT = ROOT / "results/hardware/p6_optimized_compile_20260907"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(circuit) -> dict[str, int]:
    return {
        "qubits": circuit.n_qubits,
        "depth": circuit.depth(),
        "total_gates": circuit.n_gates,
        "cz": circuit.n_gates_of_type(OpType.CZ),
        "tk2": circuit.n_gates_of_type(OpType.TK2),
        "zzphase": circuit.n_gates_of_type(OpType.ZZPhase),
        "cx": circuit.n_gates_of_type(OpType.CX),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    original = circuit_from_qasm_str(source.read_text())

    peephole = original.copy()
    FullPeepholeOptimise(
        allow_swaps=False,
        target_2qb_gate=OpType.TK2,
    ).apply(peephole)

    optimized = peephole.copy()
    NormaliseTK2().apply(optimized)
    DecomposeTK2(
        allow_swaps=False,
        # Conservative offline proxy only; this is not provider calibration.
        ZZPhase_fidelity=lambda angle: 0.9995 if abs(float(angle)) < 0.25 else 0.997,
    ).apply(optimized)

    optimized_qasm = output / "p6_optimized.qasm"
    optimized_qasm.write_text(circuit_to_qasm_str(optimized))
    metadata = {
        "schema_version": "p6-optimized-compile-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "provider_submission_performed": False,
        "source_qasm": str(source),
        "source_sha256": sha256(source),
        "optimized_qasm": str(optimized_qasm),
        "optimized_sha256": sha256(optimized_qasm),
        "passes": [
            "FullPeepholeOptimise(allow_swaps=False,target_2qb_gate=TK2)",
            "NormaliseTK2",
            "DecomposeTK2(allow_swaps=False,ZZPhase_fidelity=offline_proxy)",
        ],
        "offline_fidelity_proxy": "not a provider calibration and not a hardware prediction",
        "original": counts(original),
        "peephole_tk2": counts(peephole),
        "optimized": counts(optimized),
    }
    (output / "compile_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
