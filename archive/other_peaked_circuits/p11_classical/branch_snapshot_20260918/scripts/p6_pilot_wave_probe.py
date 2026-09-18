#!/usr/bin/env python3
"""Bounded Pilot-Wave structural feasibility probe for P6.

This intentionally stops after preparing contraction schedules.  It does not
sample P6.  The reference implementation is kept external because it is a
research dependency; pass its checkout with ``--pilot-wave-root``.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from pathlib import Path

import numpy as np


U_RE = re.compile(r"\b(?:u3|u)\(([^)]*)\)\s+\w+\[(\d+)\]")
CZ_RE = re.compile(r"\bcz\s+\w+\[(\d+)\]\s*,\s*\w+\[(\d+)\]")
QREG_RE = re.compile(r"\bqreg\s+\w+\[(\d+)\]")


def rz(angle: float) -> np.ndarray:
    return np.diag([np.exp(-0.5j * angle), np.exp(0.5j * angle)]).astype(np.complex128)


def ry(angle: float) -> np.ndarray:
    c, s = np.cos(angle / 2.0), np.sin(angle / 2.0)
    return np.array([[c, -s], [s, c]], dtype=np.complex128)


def cz() -> np.ndarray:
    return np.diag([1.0, 1.0, 1.0, -1.0]).astype(np.complex128)


def angle(expression: str) -> float:
    """Evaluate the small numeric grammar used by the canonical QASM."""
    tree = ast.parse(expression.strip().replace("pi", "PI"), mode="eval")

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id == "PI":
            return float(np.pi)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right
        raise ValueError(f"unsupported angle expression: {expression!r}")

    return visit(tree)


def load_p6(path: Path, source_limit: int | None = None):
    from pilot_wave import Circuit

    text = path.read_text()
    n_match = QREG_RE.search(text)
    if not n_match:
        raise ValueError(f"no qreg declaration in {path}")
    circuit = Circuit(int(n_match.group(1)))
    counts = {"u3": 0, "cz": 0}
    pending_rz = [np.eye(2, dtype=np.complex128) for _ in range(circuit.num_qubits)]
    # Preserve source order.  U3 = Rz(phi) Ry(theta) Rz(lambda), up to a
    # gate-global phase, which cannot affect computational-basis sampling.
    statements = [s.strip() for s in text.replace("\r", "").split(";")]
    for statement in statements:
        if not statement or statement.startswith(("OPENQASM", "include", "qreg", "creg")):
            continue
        match = U_RE.search(statement)
        if match:
            values = [angle(value) for value in match.group(1).split(",")]
            if len(values) != 3:
                raise ValueError(f"expected 3 U parameters: {statement}")
            theta, phi, lam = values
            qubit = int(match.group(2))
            # Diagonal gates commute with CZ.  Keep the post-Ry Rz pending so
            # it can be combined with the next pre-Ry Rz on this wire.
            circuit.gate(rz(phi) @ pending_rz[qubit], [qubit], name="rz_accumulated")
            circuit.gate(ry(theta), [qubit], name="ry")
            pending_rz[qubit] = rz(lam)
            counts["u3"] += 1
            if source_limit is not None and sum(counts.values()) >= source_limit:
                break
            continue
        match = CZ_RE.search(statement)
        if match:
            circuit.gate(cz(), [int(match.group(1)), int(match.group(2))], name="cz")
            counts["cz"] += 1
            if source_limit is not None and sum(counts.values()) >= source_limit:
                break
            continue
        raise ValueError(f"unsupported statement: {statement}")
    for qubit, matrix in enumerate(pending_rz):
        if not np.allclose(matrix, np.eye(2), atol=1e-14):
            circuit.gate(matrix, [qubit], name="rz_final")
    return circuit, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--pilot-wave-root", type=Path, required=True)
    parser.add_argument("--schedule", choices=("greedy", "cotengra"), default="greedy")
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--source-prefix", type=int, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.pilot_wave_root))
    from pilot_wave.tn import PreparedTensorNetwork

    circuit, source_counts = load_p6(args.qasm, args.source_prefix)
    prefix_lengths = [0, 100, 500, 1000, 2000, len(circuit.operations)]
    prefix_lengths = sorted(set(p for p in prefix_lengths if p <= len(circuit.operations)))
    started = time.perf_counter()
    prepared = PreparedTensorNetwork(
        circuit,
        prefix_lengths=prefix_lengths,
        schedule=args.schedule,
        cotengra_max_repeats=args.repeats,
        cotengra_optimizer="random-greedy",
        contraction_backend="numpy",
    )
    rows = []
    for prefix in prefix_lengths:
        plan = prepared.contraction_plans[prefix]
        peak_elements = prepared.estimate_max_intermediate_elements(prefix)
        rows.append(
            {
                "prefix": prefix,
                "plan_contractions": len(plan),
                "peak_elements": int(peak_elements),
                "peak_complex128_bytes": int(peak_elements * 16),
                "peak_gib": float(peak_elements * 16 / 2**30),
            }
        )
    result = {
        "schema": "p6-pilot-wave-feasibility-v1",
        "qasm": str(args.qasm),
        "source_counts": source_counts,
        "source_prefix_limit": args.source_prefix,
        "pilot_wave_operations": len(circuit.operations),
        "num_qubits": circuit.num_qubits,
        "schedule": args.schedule,
        "cotengra_repeats": args.repeats,
        "planner_seconds": time.perf_counter() - started,
        "rows": rows,
        "sampling_performed": False,
        "notes": [
            "U3 was decomposed into Rz-Ry-Rz; gate-global phases are irrelevant to sampling.",
            "Peak tensor size excludes repeated amplitude-query count and runtime.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
