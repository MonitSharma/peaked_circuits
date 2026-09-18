#!/usr/bin/env python3
"""P9-first bounded projected finite-horizon routing beam pilot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compiler.beam_controller import finite_horizon_beam
from structural.qasm_events import parse_qasm


def main() -> None:
    circuit = parse_qasm("data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm")
    pairs = tuple(event.wires for event in circuit.two_qubit)
    rows = []
    for width in (8, 16):
        for depth in (2, 4):
            beam = finite_horizon_beam(circuit.n_qubits, pairs, width=width, depth=depth)
            rows.append({"width": width, "depth": depth, "finalists": len(beam), "best_projected_debt": beam[0].score, "best_swaps": beam[0].swaps})
    payload = {"p9_q2": circuit.n_two_qubit, "rows": rows, "scientific_verdict": "TECHNICAL_LIMITATION", "technical_verdict": "PROJECTED_BEAM_NOT_INTEGRATED_WITH_METTLEQ_MPO_ROUTING_API", "reason": "The available production MPO runner does not expose a virtual-permutation schedule injection boundary; projected beam results are retained without claiming a P9 peak result."}
    Path("results/p11_final_campaign/beam_controller_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
