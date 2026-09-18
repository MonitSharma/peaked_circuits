#!/usr/bin/env python3
"""Quadratic sum-of-powers path graph + cut-rank (linear rank-width) screen.

Any circuit of {H, arbitrary diagonal 1Q, CZ} has a Feynman path-sum whose cost
is governed by the rank-width of a Boolean path-variable graph, a parameter
distinct from tensor-network treewidth.  P5/P6/P9 map onto that gate set
*exactly*:

    U3(t,p,l) = Rz(p) . Ry(t) . Rz(l)      and    Ry(t) = S . H . Rz(t) . H . S^dag

so  U3 = [diag] H [diag] H [diag]  -- two H per U3, no approximation.  CZ is
already diagonal.  (P8's iSWAP is Clifford but not diagonal, so it is decomposed
via iSWAP = SWAP . CZ . (S(x)S); the SWAP is a wire relabelling.)

Path graph:
  * every H on a wire ends one constant-value segment and starts another, so the
    variables are the wire segments: |vars| = #H + n_qubits;
  * each H contributes a quadratic term x_prev * x_next -> an edge along the wire;
  * each CZ contributes a quadratic term on the two current segments -> a cross
    edge;
  * arbitrary diagonal 1Q gates contribute only *unary* phase weights, so they
    add no edges. That is the structural advantage over state-based methods.

We then measure the cut-rank profile along vertex orderings.  For a bipartition
(A,B), cut-rank is the GF(2) rank of the A x B adjacency submatrix; the max over
a linear order upper-bounds linear rank-width, and rank-width <= linear
rank-width.  A small value is decisive evidence for the method; a large one is
suggestive against it.

Answer-blind: reads only circuit structure.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from structural.qasm_events import parse_qasm

HALF_PI = math.pi / 2


def build_path_graph(path: Path):
    """Return (n_vertices, edges, n_qubits, stats). Vertices are wire segments,
    numbered in creation (time) order."""
    circuit = parse_qasm(path)
    n = circuit.n_qubits
    cur = list(range(n))          # current segment variable per wire
    nxt = n                       # next fresh variable id
    edges = []
    n_h = n_cz = n_diag = 0
    # SWAP from an iSWAP decomposition is a pure wire relabelling
    perm = list(range(n))

    def add_h(q):
        nonlocal nxt, n_h
        prev = cur[q]
        cur[q] = nxt
        edges.append((prev, nxt))   # H's (-1)^{x_prev x_next} term
        nxt += 1
        n_h += 1

    for ev in circuit.events:
        if ev.gate == "u":
            q = perm[ev.wires[0]]
            # Rz(l) . [S^dag] then H then Rz(t) then H then [S] . Rz(p):
            # three diagonal blocks, two H.
            n_diag += 3
            add_h(q)
            add_h(q)
        elif ev.gate == "cz":
            a, b = perm[ev.wires[0]], perm[ev.wires[1]]
            edges.append((cur[a], cur[b]))
            n_cz += 1
        elif ev.gate == "iswap":
            # iSWAP = SWAP . CZ . (S x S); S is diagonal, SWAP relabels wires
            a, b = perm[ev.wires[0]], perm[ev.wires[1]]
            edges.append((cur[a], cur[b]))
            n_cz += 1
            n_diag += 2
            perm[ev.wires[0]], perm[ev.wires[1]] = perm[ev.wires[1]], perm[ev.wires[0]]
        elif ev.gate == "rzz":
            a, b = perm[ev.wires[0]], perm[ev.wires[1]]
            edges.append((cur[a], cur[b]))   # exp(i t Z Z) is a quadratic phase
            n_cz += 1
        else:
            raise SystemExit(f"unsupported gate for SOP construction: {ev.gate}")

    return nxt, edges, n, {"h_gates": n_h, "quadratic_phase_terms": n_cz,
                           "diagonal_blocks": n_diag}


def cut_rank(adj_bits, order, k, nv):
    """GF(2) rank of the A x B adjacency submatrix for A = order[:k]."""
    inB = bytearray(nv)
    for v in order[k:]:
        inB[v] = 1
    # restrict each A-row to B, then row-reduce over GF(2)
    pivots = {}
    rank = 0
    for v in order[:k]:
        row = 0
        for u in adj_bits[v]:
            if inB[u]:
                row |= 1 << u
        while row:
            h = row.bit_length() - 1
            if h not in pivots:
                pivots[h] = row
                rank += 1
                break
            row ^= pivots[h]
    return rank


def analyse(path: Path, n_cuts: int = 40):
    nv, edges, nq, stats = build_path_graph(path)
    adj = [[] for _ in range(nv)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    order = list(range(nv))   # creation/time order
    positions = [max(1, round(nv * i / (n_cuts + 1))) for i in range(1, n_cuts + 1)]
    profile = []
    best = 0
    for k in positions:
        r = cut_rank(adj, order, k, nv)
        profile.append({"k": k, "cut_rank": r})
        best = max(best, r)
    return {"circuit": path.name, "n_qubits": nq, "n_vertices": nv,
            "n_edges": len(edges), **stats,
            "max_cut_rank_time_order": best,
            "implied_cost_log2": 2 * best,
            "profile": profile}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", nargs="+", type=Path)
    ap.add_argument("--cuts", type=int, default=40)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = []
    for q in args.qasm:
        r = analyse(q, args.cuts)
        out.append(r)
        print(f"  {r['circuit']}: n={r['n_qubits']} vars={r['n_vertices']} "
              f"edges={r['n_edges']} H={r['h_gates']}  ->  max cut-rank "
              f"{r['max_cut_rank_time_order']}  (cost ~ 4^{r['max_cut_rank_time_order']} "
              f"= 2^{r['implied_cost_log2']})", flush=True)
    if args.out:
        args.out.write_text(json.dumps({"schema": "sop-rank-width-v1",
                                        "answer_blind": True, "results": out}, indent=2))


if __name__ == "__main__":
    main()
