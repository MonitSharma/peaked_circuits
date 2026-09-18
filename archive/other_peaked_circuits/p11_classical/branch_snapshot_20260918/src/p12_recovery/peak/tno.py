"""Generic TNO naming/decoding boundary.

The underlying Quimb implementation is optional. Product marginals are exposed
as a diagnostic decoder and are never labelled joint MAP evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def product_marginal_decoder(state: Any) -> tuple[str, list[float]]:
    """Decode independent marginals for diagnostics only."""
    probabilities: list[float] = []
    for site in state.sites:
        value = state.local_expectation([[1.0, 0.0], [0.0, 0.0]], where=[site], max_bond=2, normalized=True, optimize="greedy").real.item()
        probabilities.append(float(value))
    return "".join("0" if value >= 0.5 else "1" for value in probabilities), probabilities


def method_metadata(*, max_bond: int, cutoff: float, answer_blind: bool = True) -> dict[str, Any]:
    return {"method_family": "TNO", "max_bond": max_bond, "cutoff": cutoff, "decoder": "product_marginal_diagnostic", "joint_map_claim": False, "answer_blind": answer_blind}


def contract_qasm(path: str | Path, *, max_bond: int = 16, cutoff: float = 0.1,
                  chunk_size: int = 4, max_seconds: float = 120.0) -> dict[str, Any]:
    """Run the bounded greedy TNO core on a generic OpenQASM 2 circuit."""
    import importlib

    QuantumCircuit = importlib.import_module("qiskit").QuantumCircuit
    tno = importlib.import_module("p12_recovery.bluequbit.tno")

    circuit = QuantumCircuit.from_qasm_file(str(path))
    circuit.remove_final_measurements()
    layers = list(tno.iter_layers(circuit))
    core, trace, timed_out = tno.contract_core(layers, chunk_size=chunk_size,
                                           max_bond=max_bond, cutoff=cutoff,
                                           max_seconds=max_seconds)
    result: dict[str, Any] = {"method_family": "TNO", "status": "TIMEOUT" if timed_out else "CORE_COMPLETE", "answer_blind": True, "max_bond": max_bond, "cutoff": cutoff, "trace": trace, "joint_map_claim": False}
    if not timed_out:
        state = tno.finish_state(core, max_bond=max_bond, cutoff=cutoff)
        result["product_marginal_diagnostic"] = product_marginal_decoder(state)
    return result
