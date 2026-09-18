#!/usr/bin/env python3
"""Find, but do not execute, a native P8 fixed-amplitude contraction tree."""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

from cotengra import HyperOptimizer
from quimb.tensor import Circuit

from structural.qasm_events import parse_qasm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--output-bitstring", default=None)
    parser.add_argument("--max-time", type=float, default=300.0)
    parser.add_argument("--repeats", type=int, default=32)
    args = parser.parse_args()

    parsed = parse_qasm(args.qasm)
    bitstring = args.output_bitstring or ("0" * parsed.n_qubits)
    if len(bitstring) != parsed.n_qubits or set(bitstring) - {"0", "1"}:
        raise SystemExit("output bitstring must contain exactly n_qubits binary characters")

    circuit = Circuit(parsed.n_qubits, gate_contract="split-gate")
    for event in parsed.events:
        if event.gate == "u":
            circuit.u3(*event.params, event.wires[0])
        elif event.gate == "iswap":
            circuit.iswap(*event.wires)
        elif event.gate == "cz":
            circuit.cz(*event.wires)
        else:
            raise SystemExit(f"unsupported native P8 gate: {event.gate}")

    optimizer = HyperOptimizer(
        methods=["greedy", "random-greedy"],
        minimize="combo",
        max_repeats=args.repeats,
        max_time=args.max_time,
        parallel=False,
        progbar=False,
    )
    started = time.monotonic()
    rehearsed = circuit.amplitude_rehearse(
        bitstring,
        optimize=optimizer,
        simplify_sequence="",
        rehearse=True,
    )
    tree = rehearsed["tree"]
    base_flops = int(tree.total_flops())
    base_size = int(tree.max_size())
    base_width = float(tree.contraction_width())
    budgets = {"4GB": 4 * 1024**3, "16GB": 16 * 1024**3,
               "32GB": 32 * 1024**3, "64GB": 64 * 1024**3}
    slices = {}
    for label, bytes_budget in budgets.items():
        sliced = tree.copy()
        target_elements = max(1, bytes_budget // 16)  # complex128
        sliced.slice(target_size=target_elements, inplace=True, max_repeats=16, seed=2026)
        flops = int(sliced.total_flops())
        slices[label] = {
            "budget_bytes": bytes_budget,
            "target_elements_complex128": target_elements,
            "number_of_slices": int(sliced.nslices),
            "max_tensor_elements": int(sliced.max_size()),
            "contraction_width_log2": float(sliced.contraction_width()),
            "estimated_flops": flops,
            "slicing_overhead_flops_ratio": flops / base_flops if base_flops else None,
            "slicing_overhead_log2_flops": math.log2(flops / base_flops) if flops and base_flops else None,
        }
    result = {
        "schema": "p8-native-amplitude-contraction-rehearsal-v1",
        "qasm": str(args.qasm.resolve()),
        "n_qubits": parsed.n_qubits,
        "event_count": len(parsed.events),
        "gate_counts": {gate: sum(e.gate == gate for e in parsed.events) for gate in ("u", "iswap", "cz")},
        "input_bitstring": "0" * parsed.n_qubits,
        "output_bitstring": bitstring,
        "optimizer": {"methods": ["greedy", "random-greedy"], "minimize": "combo", "max_repeats": args.repeats, "max_time_s": args.max_time},
        "network_tensors_after_rehearsal": len(rehearsed["tn"].tensors),
        "contraction_width_log2": base_width,
        "estimated_flops": base_flops,
        "largest_tensor_elements": base_size,
        "largest_tensor_bytes_complex128": base_size * 16,
        "slices": slices,
        "rehearsal_runtime_s": time.monotonic() - started,
        "contracted": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
