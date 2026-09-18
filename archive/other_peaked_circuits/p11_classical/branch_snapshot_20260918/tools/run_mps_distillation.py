#!/usr/bin/env python3
"""Run one reproducible low-bond MPS marginal-distillation experiment.

The circuit inputs are plain OpenQASM 2 files containing the gate vocabulary
used by the peaked P9/P11 circuits: ``u``, ``cz``, and ``rzz``. The numerical
state engine is the pinned local MettleQ checkout. This wrapper deliberately
reports one-bit marginals and truncation diagnostics; it never requires or
computes a full statevector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from mettleq._mlx_compat import mx
from mettleq.mps_state import MPSOptions, MPSState

_QREG = re.compile(r"qreg\s+q\[(\d+)\]")
_U = re.compile(r"u\(([^)]*)\)\s+q\[(\d+)\]")
_CZ = re.compile(r"cz\s+q\[(\d+)\],q\[(\d+)\]")
_RZZ = re.compile(r"rzz\(([^)]*)\)\s+q\[(\d+)\],q\[(\d+)\]")


def _expr(value: str) -> float:
    value = value.strip().replace("pi", "math.pi")
    # The canonical files use only numeric expressions and pi fractions.
    if not re.fullmatch(r"[0-9eE+\-*/(). mathpi]+", value):
        raise ValueError(f"unsupported QASM parameter expression: {value!r}")
    return float(eval(value, {"__builtins__": {}}, {"math": math}))


def parse_qasm(path: Path) -> tuple[int, list[dict[str, Any]]]:
    operations: list[dict[str, Any]] = []
    n_qubits: int | None = None
    for line_number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line or line.startswith(("OPENQASM", "include", "creg")):
            continue
        match = _QREG.fullmatch(line.rstrip(";"))
        if match:
            n_qubits = int(match.group(1))
            continue
        for name, pattern in (("u", _U), ("cz", _CZ), ("rzz", _RZZ)):
            match = pattern.fullmatch(line.rstrip(";"))
            if match:
                if name == "u":
                    theta, phi, lam = (_expr(x) for x in match.group(1).split(","))
                    operations.append(
                        {"name": name, "params": [theta, phi, lam], "wires": [int(match.group(2))]}
                    )
                elif name == "rzz":
                    operations.append(
                        {
                            "name": name,
                            "params": [_expr(match.group(1))],
                            "wires": [int(match.group(2)), int(match.group(3))],
                        }
                    )
                else:
                    operations.append(
                        {
                            "name": name,
                            "params": [],
                            "wires": [int(match.group(1)), int(match.group(2))],
                        }
                    )
                break
        else:
            raise ValueError(f"unsupported QASM at {path}:{line_number}: {raw}")
    if n_qubits is None:
        raise ValueError(f"no qreg declaration in {path}")
    return n_qubits, operations


def _u_matrix(theta: float, phi: float, lam: float, dtype: np.dtype = np.dtype("complex128")) -> np.ndarray:
    c, s = math.cos(theta / 2.0), math.sin(theta / 2.0)
    return np.array(
        [[c, -np.exp(1j * lam) * s], [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]],
        dtype=dtype,
    )


_CZ_MATRIX = np.diag(np.array([1, 1, 1, -1], dtype=np.complex128))
_Z = np.diag(np.array([1, -1], dtype=np.complex128))


def _rss_bytes() -> int:
    own = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # macOS reports ru_maxrss in bytes; Linux reports KiB.
    if sys.platform != "darwin":
        own *= 1024
    try:
        import psutil  # type: ignore[import-not-found]

        proc = psutil.Process()
        total = proc.memory_info().rss
        total += sum(child.memory_info().rss for child in proc.children(recursive=True))
        return max(own, int(total))
    except Exception:
        return own


def _checkpoint(state: MPSState, outdir: Path, step: int, metadata: dict[str, Any]) -> None:
    arrays = {f"A_{i}": np.asarray(tensor) for i, tensor in enumerate(state.A)}
    np.savez_compressed(outdir / f"checkpoint_{step:06d}.npz", **arrays)
    (outdir / f"checkpoint_{step:06d}.json").write_text(json.dumps(metadata, indent=2) + "\n")


def _initial_layout(ordering: str, n: int, operations: list[dict[str, Any]], seed: int | None) -> list[int]:
    if ordering == "auto":
        ordering = "random" if seed is not None else "original"
    if ordering == "original":
        return list(range(n))
    if ordering == "reversed":
        return list(reversed(range(n)))
    if ordering in {"weighted_degree_desc", "weighted_degree_asc"}:
        degree = [0] * n
        for operation in operations:
            if len(operation["wires"]) == 2:
                a, b = operation["wires"]
                degree[a] += 1
                degree[b] += 1
        reverse = ordering.endswith("_desc")
        return sorted(range(n), key=lambda q: (-degree[q] if reverse else degree[q], q))
    if ordering in {"fiedler", "rcm"}:
        adjacency = np.zeros((n, n), dtype=float)
        for operation in operations:
            if len(operation["wires"]) == 2:
                a, b = operation["wires"]
                adjacency[a, b] += 1.0
                adjacency[b, a] += 1.0
        if ordering == "fiedler":
            laplacian = np.diag(adjacency.sum(axis=1)) - adjacency
            values, vectors = np.linalg.eigh(laplacian)
            vector = vectors[:, 1] if len(values) > 1 else np.arange(n)
            return sorted(range(n), key=lambda q: (vector[q], q))
        from scipy.sparse.csgraph import reverse_cuthill_mckee
        return reverse_cuthill_mckee(adjacency, symmetric_mode=True).tolist()
    if ordering == "random":
        rng = np.random.default_rng(seed)
        return rng.permutation(n).tolist()
    raise ValueError(f"unsupported initial ordering: {ordering}")


def run(args: argparse.Namespace) -> dict[str, Any]:
    qasm = args.qasm.resolve()
    n, operations = parse_qasm(qasm)
    if n > 128:
        raise ValueError("refusing an input larger than 128 qubits")
    initial_layout = _initial_layout(args.ordering, n, operations, args.routing_seed)

    options = MPSOptions(
        dmax=args.max_bond,
        eps=args.cutoff,
        svd_driver=args.svd_driver,
        routing_strategy=args.routing_strategy,
        routing_lookahead=args.routing_lookahead,
        renormalize_splits=True,
    )
    state = MPSState(n, options)
    state.site_to_logical = list(initial_layout)
    state.logical_to_site = [0] * n
    for site, logical in enumerate(initial_layout):
        state.logical_to_site[logical] = site

    if args.routing_strategy == "lookahead":
        pairs = [tuple(op["wires"]) for op in operations if len(op["wires"]) == 2]
        state.prepare_routing(pairs)

    started = time.perf_counter()
    for step, op in enumerate(operations, 1):
        if op["name"] == "u":
            state.apply_logical_single(
                mx.array(_u_matrix(*op["params"], dtype=np.dtype(args.dtype))),
                op["wires"][0],
            )
        elif op["name"] == "cz":
            state.apply_logical_two(mx.array(_CZ_MATRIX), *op["wires"])
        elif op["name"] == "rzz":
            # QASM RZZ(theta) = exp(-i theta/2 Z⊗Z); MettleQ's helper takes
            # the coefficient of Z⊗Z directly.
            state.apply_logical_zz_phase(op["params"][0] / 2.0, *op["wires"])
        if args.checkpoint_every and step % args.checkpoint_every == 0:
            _checkpoint(
                state,
                args.outdir,
                step,
                {
                    "step": step,
                    "rss_bytes": _rss_bytes(),
                    "elapsed_s": time.perf_counter() - started,
                },
            )

    p1: list[float] = []
    for logical in range(n):
        z = float(np.real(state.expectation_product({logical: _Z})))
        p1.append(float(np.clip((1.0 - z) / 2.0, 0.0, 1.0)))
    m = [x - 0.5 for x in p1]
    predicted = [int(x >= 0.5) for x in p1]
    confidence = [2.0 * abs(x) for x in m]
    samples = None
    sample_se = [None] * n
    if args.samples:
        samples = state.sample_array(
            args.samples, wires=list(range(n)), rng=np.random.default_rng(args.sampling_seed)
        )
        sample_p1 = np.mean(samples, axis=0)
        sample_se = [float(math.sqrt(max(0.0, x * (1.0 - x)) / args.samples)) for x in sample_p1]
    elapsed = time.perf_counter() - started
    result = {
        "schema": "p11-distillation-run-v1",
        "circuit": {
            "path": str(qasm),
            "sha256": hashlib.sha256(qasm.read_bytes()).hexdigest(),
            "n_qubits": n,
            "n_operations": len(operations),
        },
        "configuration": {
            "max_bond": args.max_bond,
            "cutoff": args.cutoff,
            "dtype": args.dtype,
            "routing_strategy": args.routing_strategy,
            "routing_lookahead": args.routing_lookahead,
            "ordering": args.ordering,
            "routing_seed": args.routing_seed,
            "sampling_seed": args.sampling_seed,
            "samples": args.samples,
            "svd_driver": args.svd_driver,
        },
        "marginals": [
            {
                "logical_qubit": i,
                "p0": 1.0 - p1[i],
                "p1": p1[i],
                "margin": m[i],
                "confidence": confidence[i],
                "predicted_bit": predicted[i],
                "sample_standard_error": sample_se[i],
            }
            for i in range(n)
        ],
        "final_logical_to_site": list(state.logical_to_site),
        "diagnostics": {
            "max_bond_ever": state.max_bond_ever,
            "mean_bond_final": float(np.mean(state.bonds)) if state.bonds else 1.0,
            "truncation_events": state.trunc_events,
            "relative_discarded_weight_sum": state.relative_discarded_weight_sum,
            "relative_discarded_weight_max": state.relative_discarded_weight_max,
            "local_discarded_weight_sum": state.local_discarded_weight_sum,
            "local_discarded_weight_max": state.local_discarded_weight_max,
            "norm": state.norm(),
            "routing_swaps": state.routing_swaps,
            "svd_calls": state.svd_calls,
        },
        "runtime_s": elapsed,
        "peak_rss_bytes": _rss_bytes(),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "git_commit": subprocess.check_output(
                ["git", "-C", str(args.outdir.parent.parent), "rev-parse", "HEAD"], text=True
            ).strip()
            if (args.outdir.parent.parent / ".git").exists()
            else None,
        },
    }
    if samples is not None:
        result["sample_marginals"] = [float(x) for x in np.mean(samples, axis=0)]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--max-bond", type=int, required=True)
    parser.add_argument("--cutoff", type=float, required=True)
    parser.add_argument("--dtype", default="complex64")
    parser.add_argument("--routing-strategy", choices=["restore", "lookahead"], default="restore")
    parser.add_argument("--routing-lookahead", type=int, default=8)
    parser.add_argument(
        "--ordering",
        choices=["auto", "original", "reversed", "weighted_degree_desc", "weighted_degree_asc", "fiedler", "rcm", "random"],
        default="auto",
        help="Initial logical-to-site ordering; auto preserves the historical behavior.",
    )
    parser.add_argument("--routing-seed", type=int, default=0)
    parser.add_argument("--sampling-seed", type=int, default=0)
    parser.add_argument("--samples", type=int, default=0)
    parser.add_argument("--checkpoint-every", type=int, default=0)
    parser.add_argument("--svd-driver", choices=["auto", "gesdd", "gesvd", "numpy"], default="auto")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    result = run(args)
    (args.outdir / "run.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "run": str(args.outdir / "run.json"),
                "n_qubits": result["circuit"]["n_qubits"],
                "runtime_s": result["runtime_s"],
                "peak_rss_bytes": result["peak_rss_bytes"],
                "max_bond": result["diagnostics"]["max_bond_ever"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
