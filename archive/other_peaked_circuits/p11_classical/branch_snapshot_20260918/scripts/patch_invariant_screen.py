#!/usr/bin/env python3
"""Screen for a hidden U / U-dagger pairing via local-unitary patch invariants.

The HQAP construction is  T[R] > T[U] > U^dag > P, where T applies coordinated
swaps, angle sweeping and masking.  Earlier scans looked for a single global
permutation and found nothing; the generator says the relevant object is a
*time-dependent* permutation, so a fixed mapping is expected to fail.

Before building a sequential permutation decoder, test the cheap necessary
condition it depends on:

    a permutation relabels WHERE two-qubit patches sit, not WHICH patches exist.

So if C[:s] contains T[U] and C[s:] contains U^dag, the *multiset* of
local-unitary invariants of their maximal two-qubit patches must match --
regardless of any qubit relabelling.  Angle sweeping and masking perturb the
invariants slightly, so we compare distributions, not assignments.

Invariant used: the Weyl/Cartan coordinates (a,b,c) of each patch unitary, which
are invariant under local single-qubit rotations on either side -- exactly the
freedom that sweeping and masking exploit.

If no boundary s yields matching clouds, a sequential decoder has nothing to
recover and the route closes for hours of work instead of days.

Answer-blind: reads only circuit structure.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from structural.qasm_events import parse_qasm
from structural.patch_unitary import gate_matrix

from qiskit.synthesis import TwoQubitWeylDecomposition


def maximal_patches(events, n_qubits):
    """Group the event stream into maximal 2-qubit blocks: consecutive ops on a
    pair, uninterrupted by either wire interacting with a third qubit."""
    pending = defaultdict(list)          # pair -> [events]
    last_1q = defaultdict(list)          # wire -> [events] awaiting a partner
    patches = []

    def flush(pair):
        if pending[pair]:
            patches.append((pair, pending[pair]))
            pending[pair] = []

    for ev in events:
        if len(ev.wires) == 1:
            q = ev.wires[0]
            last_1q[q].append(ev)
        else:
            a, b = sorted(ev.wires)
            # any open block on a or b with a different partner must close
            for pair in [p for p in list(pending) if (a in p or b in p) and p != (a, b)]:
                flush(pair)
            pending[(a, b)].extend(last_1q[a] + last_1q[b] + [ev])
            last_1q[a] = []
            last_1q[b] = []
    for pair in list(pending):
        flush(pair)
    return patches


def weyl_coords(pair, evs):
    u = np.eye(4, dtype=complex)
    a, b = pair
    for ev in evs:
        g = gate_matrix(ev)
        if len(ev.wires) == 1:
            loc = 0 if ev.wires[0] == a else 1
            full = np.kron(np.eye(2), g) if loc == 0 else np.kron(g, np.eye(2))
        else:
            full = g if tuple(ev.wires) == (a, b) else g  # cz/iswap symmetric
        u = full @ u
    try:
        d = TwoQubitWeylDecomposition(u)
        return (float(d.a), float(d.b), float(d.c))
    except Exception:
        return None


def cloud(circuit, lo, hi, conjugate=False):
    evs = circuit.events[lo:hi]
    if conjugate:
        evs = list(reversed(evs))
    pts = []
    for pair, group in maximal_patches(evs, circuit.n_qubits):
        w = weyl_coords(pair, group)
        if w is not None:
            pts.append(w)
    return np.array(pts) if pts else np.zeros((0, 3))


def emd_like(x, y, bins=12):
    """Symmetric histogram distance over the Weyl chamber; 0 = identical clouds."""
    if len(x) == 0 or len(y) == 0:
        return 1.0
    rng = [(0, np.pi / 4), (0, np.pi / 4), (-np.pi / 4, np.pi / 4)]
    hx, _ = np.histogramdd(x, bins=bins, range=rng)
    hy, _ = np.histogramdd(y, bins=bins, range=rng)
    hx = hx / max(hx.sum(), 1)
    hy = hy / max(hy.sum(), 1)
    return float(0.5 * np.abs(hx - hy).sum())


def screen(path: Path, n_boundaries: int = 21):
    c = parse_qasm(path)
    total = len(c.events)
    out = []
    for i in range(1, n_boundaries + 1):
        s = round(total * i / (n_boundaries + 1))
        left = cloud(c, 0, s)
        right = cloud(c, s, total, conjugate=True)
        d = emd_like(left, right)
        out.append({"boundary_frac": s / total, "s": s,
                    "n_left_patches": len(left), "n_right_patches": len(right),
                    "cloud_distance": d})
        print(f"    s={s/total:.2f} ({s:6d})  patches L={len(left):5d} R={len(right):5d}"
              f"   cloud distance {d:.4f}", flush=True)
    best = min(out, key=lambda r: r["cloud_distance"])
    return {"circuit": path.name, "n_events": total, "boundaries": out,
            "best_boundary_frac": best["boundary_frac"],
            "best_cloud_distance": best["cloud_distance"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", nargs="+", type=Path)
    ap.add_argument("--boundaries", type=int, default=21)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    res = []
    for q in args.qasm:
        print(f"  === {q.name} ===")
        r = screen(q, args.boundaries)
        res.append(r)
        print(f"    -> best boundary {r['best_boundary_frac']:.2f}, "
              f"distance {r['best_cloud_distance']:.4f}\n")
    if args.out:
        args.out.write_text(json.dumps({"schema": "patch-invariant-screen-v1",
                                        "answer_blind": True, "results": res}, indent=2))


if __name__ == "__main__":
    main()
