"""Contract a saved P8 MPO handoff with consolidated residual tails.

The bulk MPO solver intentionally stops before its final unswap attractor and
writes ``mpo_dump.pkl``.  This script consumes that exact factor and applies
each residual side as one MPO operator, so the tail is contracted globally per
side instead of layer-by-layer.  No routing decisions are made here.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--solver-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-bond", type=int, default=4096)
    parser.add_argument("--cutoff", type=float, default=0.0)
    parser.add_argument(
        "--tail-chunk-work",
        type=int,
        default=4,
        help="Maximum unitary operations, including SWAPs, per staged tail chunk.",
    )
    parser.add_argument("--samples", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=32)
    parser.add_argument("--save-state", type=Path, default=None)
    return parser


def _require_mapping(bundle, nqubits):
    interface = bundle.get("factor_interface")
    mapping = bundle.get("mapping_metadata")
    if not isinstance(interface, dict) or not isinstance(mapping, dict):
        raise SystemExit("candidate output refused: handoff mapping contract is absent")
    required = (
        "factor_site_to_original_logical",
        "original_logical_to_factor_site",
        "routing_permutation",
        "qasm_q0_first_mapping",
        "portal_output_convention",
    )
    if any(mapping.get(key) is None for key in required):
        raise SystemExit("candidate output refused: handoff mapping contract is incomplete")
    site_to_logical = mapping["factor_site_to_original_logical"]
    logical_to_site = mapping["original_logical_to_factor_site"]
    if (sorted(site_to_logical) != list(range(nqubits)) or
            sorted(logical_to_site) != list(range(nqubits))):
        raise SystemExit("candidate output refused: handoff mapping is not a permutation")
    return mapping


def _load_solver(solver_root: Path):
    src = solver_root / "src"
    if not (src / "p9solver").is_dir():
        raise SystemExit(f"p9solver package not found under {src}")
    sys.path.insert(0, str(src))
    from p9solver.mpo import mpo_from_circuit
    from p9solver.qiskit_utils import merge_layers
    from qiskit_quimb import quimb_circuit
    from quimb.tensor import Circuit, CircuitMPS

    return Circuit, CircuitMPS, quimb_circuit, mpo_from_circuit, merge_layers


def _tail_chunks(
    layers, *, inverse, merge_layers, iter_layers, chunk_work
):
    if not layers:
        return []
    circuit = merge_layers(layers)
    # Handoff bundles retain measurement layers for the normal decoder. They
    # are not part of the unitary tail and cannot be inverted by Qiskit.
    circuit.remove_final_measurements(inplace=True)
    if inverse:
        circuit = circuit.inverse()
    unitary_layers = list(iter_layers(circuit))
    chunks = []
    current = []
    work = 0
    ignored = {"measure", "barrier", "delay"}
    for layer in unitary_layers:
        count = sum(
            value for name, value in layer.count_ops().items() if name not in ignored
        )
        if current and work + count > chunk_work:
            chunks.append(current)
            current, work = [], 0
        current.append(layer)
        work += count
    if current:
        chunks.append(current)
    return chunks


def _as_tail_mpo(
    layers, *, inverse, Circuit, quimb_circuit, mpo_from_circuit, merge_layers
):
    circuit = merge_layers(layers)
    circuit.remove_final_measurements(inplace=True)
    if inverse:
        circuit = circuit.inverse()
    return mpo_from_circuit(quimb_circuit(circuit.decompose("unitary"), Circuit))


def main() -> int:
    args = _parser().parse_args()
    Circuit, CircuitMPS, quimb_circuit, mpo_from_circuit, merge_layers = _load_solver(
        args.solver_root.resolve()
    )
    from p9solver.qiskit_utils import iter_layers
    with args.bundle.open("rb") as handle:
        bundle = pickle.load(handle)
    core = bundle["mpo"]
    left_layers = bundle.get("layers_left") or []
    right_layers = bundle.get("layers_right") or []
    interface = bundle.get("factor_interface")
    if interface is not None:
        mapping = interface.get("factor_site_to_original_logical")
        if not isinstance(mapping, list) or sorted(mapping) != list(range(len(core.sites))):
            raise SystemExit(
                "bundle contains factor_interface but its site/logical permutation is invalid"
            )
    nqubits = len(core.sites)
    mapping = _require_mapping(bundle, nqubits) if args.samples else None
    started = time.perf_counter()

    initial = quimb_circuit(
        __import__("qiskit").QuantumCircuit(nqubits),
        quimb_circuit_class=CircuitMPS,
    ).psi
    if args.tail_chunk_work < 1:
        raise SystemExit("--tail-chunk-work must be positive")
    left_chunks = _tail_chunks(
        left_layers,
        inverse=True,
        merge_layers=merge_layers,
        iter_layers=iter_layers,
        chunk_work=args.tail_chunk_work,
    )
    right_chunks = _tail_chunks(
        right_layers,
        inverse=False,
        merge_layers=merge_layers,
        iter_layers=iter_layers,
        chunk_work=args.tail_chunk_work,
    )

    state = initial
    for chunk in left_chunks:
        left_tail = _as_tail_mpo(
            chunk,
            inverse=False,
            Circuit=Circuit,
            quimb_circuit=quimb_circuit,
            mpo_from_circuit=mpo_from_circuit,
            merge_layers=merge_layers,
        )
        state = left_tail.apply(
            state, compress=True, max_bond=args.max_bond, cutoff=args.cutoff
        )
    state = core.apply(
        state, compress=True, max_bond=args.max_bond, cutoff=args.cutoff
    )
    for chunk in right_chunks:
        right_tail = _as_tail_mpo(
            chunk,
            inverse=False,
            Circuit=Circuit,
            quimb_circuit=quimb_circuit,
            mpo_from_circuit=mpo_from_circuit,
            merge_layers=merge_layers,
        )
        state = right_tail.apply(
            state, compress=True, max_bond=args.max_bond, cutoff=args.cutoff
        )

    if args.save_state is not None:
        args.save_state.parent.mkdir(parents=True, exist_ok=True)
        with args.save_state.open("wb") as handle:
            pickle.dump(state, handle, protocol=pickle.HIGHEST_PROTOCOL)

    sampled_top = []
    sample_unique = 0
    if args.samples:
        if args.samples < 0:
            raise SystemExit("--samples must be non-negative")
        pairs = list(state.sample(args.samples))
        counts = Counter("".join(str(bit) for bit in bits) for bits, _ in pairs)
        sample_unique = len(counts)
        sampled_top = counts.most_common(args.top_k)

    summary = {
        "schema_version": "p8-tail-contraction.v1",
        "bundle": str(args.bundle.resolve()),
        "solver_root": str(args.solver_root.resolve()),
        "left_layers": len(left_layers),
        "right_layers": len(right_layers),
        "left_chunks": len(left_chunks),
        "right_chunks": len(right_chunks),
        "tail_chunk_work": args.tail_chunk_work,
        "left_work_ops": sum(
            sum(v for k, v in layer.count_ops().items() if k not in {"swap", "measure", "barrier", "delay"})
            for layer in left_layers
        ),
        "right_work_ops": sum(
            sum(v for k, v in layer.count_ops().items() if k not in {"swap", "measure", "barrier", "delay"})
            for layer in right_layers
        ),
        "max_bond": args.max_bond,
        "cutoff": args.cutoff,
        "final_max_bond": int(state.max_bond()),
        "final_norm": float(state.norm()),
        "elapsed_s": time.perf_counter() - started,
        "virtual_tail_frames": bundle.get("virtual_tail_frames"),
        "factor_interface": bundle.get("factor_interface"),
        "mapping_status": "validated" if mapping is not None else "not_required",
        "mapping_metadata": mapping,
        "samples": args.samples,
        "sample_unique": sample_unique,
        "sample_top_k": sampled_top,
        "save_state": str(args.save_state.resolve()) if args.save_state else None,
        "status": "completed",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
