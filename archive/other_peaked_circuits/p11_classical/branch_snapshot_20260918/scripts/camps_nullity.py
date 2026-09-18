#!/usr/bin/env python3
"""CAMPS / OFD feasibility diagnostic: GF(2) rank profile of Clifford-conjugated
Pauli rotations.

A Clifford-augmented MPS writes the state as ``C |phi>`` with ``C`` Clifford and
``|phi>`` an MPS.  Clifford gates are absorbed into ``C`` for free.  A non-Clifford
rotation ``R_P(theta)`` becomes

    R_P(theta) C |phi>  =  C R_{P'}(theta) |phi>,     P' = C^dag P C

so only the *conjugated* rotations ever touch the MPS.  Across an MPS bond cut
``k``, the bond dimension is bounded by ``2^nu(k)`` where ``nu(k)`` is the GF(2)
rank of the conjugated Pauli strings that straddle the cut (restricted to one
side).  Rotations that do not straddle a cut cost nothing there, and
GF(2)-dependent ones do not compound.

So ``max_k nu(k)`` is a go/no-go for CAMPS:
    nu <~ 20   -> bond <= ~1e6, tractable
    nu >~ 40   -> bond >= ~1e12, hopeless

Phases are irrelevant to this structure, so Paulis are tracked purely
symplectically as ``(x|z)`` over GF(2).

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


def _is_multiple_of_half_pi(angle: float, tol: float = 1e-8) -> bool:
    return abs(angle / HALF_PI - round(angle / HALF_PI)) < tol


class Frame:
    """Symplectic Clifford frame.

    Stores, for each qubit j, the images ``C^dag X_j C`` and ``C^dag Z_j C`` as
    bitmask pairs over the 2n symplectic coordinates.  Appending a Clifford gate
    ``G`` (so ``C -> G C``) rewrites only the entries of the qubits ``G`` acts on,
    using ``C^dag G^dag P G C``.
    """

    def __init__(self, n: int) -> None:
        self.n = n
        # x_img[j], z_img[j] are (x_mask, z_mask) pairs of n-bit ints
        self.x_img = [(1 << j, 0) for j in range(n)]
        self.z_img = [(0, 1 << j) for j in range(n)]

    @staticmethod
    def _xor(a, b):
        return (a[0] ^ b[0], a[1] ^ b[1])

    def apply_h(self, q: int) -> None:
        # H X H = Z, H Z H = X  -> swap the images
        self.x_img[q], self.z_img[q] = self.z_img[q], self.x_img[q]

    def apply_s(self, q: int) -> None:
        # S^dag X S = Y = X.Z (symplectically x|z both set); Z unchanged
        self.x_img[q] = self._xor(self.x_img[q], self.z_img[q])

    def apply_cz(self, a: int, b: int) -> None:
        # CZ X_a CZ = X_a Z_b ; CZ X_b CZ = X_b Z_a ; Z's unchanged
        xa, xb = self.x_img[a], self.x_img[b]
        self.x_img[a] = self._xor(xa, self.z_img[b])
        self.x_img[b] = self._xor(xb, self.z_img[a])

    def apply_swap(self, a: int, b: int) -> None:
        self.x_img[a], self.x_img[b] = self.x_img[b], self.x_img[a]
        self.z_img[a], self.z_img[b] = self.z_img[b], self.z_img[a]

    def apply_iswap(self, a: int, b: int) -> None:
        # iSWAP(a,b) = SWAP . CZ . (S ⊗ S), so S⊗S acts first under C -> G C.
        self.apply_s(a)
        self.apply_s(b)
        self.apply_cz(a, b)
        self.apply_swap(a, b)

    def conj_z(self, q: int):
        return self.z_img[q]

    def conj_y(self, q: int):
        return self._xor(self.x_img[q], self.z_img[q])


class CutBasis:
    """Incremental GF(2) row-echelon basis, one per MPS bond cut."""

    def __init__(self) -> None:
        self.pivots: dict[int, int] = {}

    def add(self, vec: int) -> bool:
        while vec:
            high = vec.bit_length() - 1
            if high not in self.pivots:
                self.pivots[high] = vec
                return True
            vec ^= self.pivots[high]
        return False

    @property
    def rank(self) -> int:
        return len(self.pivots)


def analyse(path: Path, sample_every: int = 250):
    circuit = parse_qasm(path)
    n = circuit.n_qubits
    frame = Frame(n)
    cuts = [CutBasis() for _ in range(n - 1)]  # cut k splits [0..k] | [k+1..n-1]
    left_masks = [(1 << (k + 1)) - 1 for k in range(n - 1)]

    n_clifford = n_nonclifford = 0
    profile = []

    def record_rotation(pauli):
        nonlocal n_nonclifford
        n_nonclifford += 1
        xm, zm = pauli
        support = xm | zm
        for k in range(n - 1):
            left = left_masks[k]
            l_sup = support & left
            r_sup = support & ~left
            if l_sup and r_sup:  # straddles this cut
                # Restrict to the SMALLER side: the Schmidt rank across a cut is
                # bounded by the smaller subsystem, so restricting to the larger
                # side inflates edge cuts into meaninglessly large ranks.
                if (k + 1) <= (n - k - 1):
                    vec = ((xm & left) << n) | (zm & left)
                else:
                    vec = ((xm & ~left) << n) | (zm & ~left)
                cuts[k].add(vec)

    for idx, ev in enumerate(circuit.events):
        if ev.gate == "cz":
            frame.apply_cz(ev.wires[0], ev.wires[1])
            n_clifford += 1
        elif ev.gate == "iswap":
            frame.apply_iswap(ev.wires[0], ev.wires[1])
            n_clifford += 1
        elif ev.gate == "rzz":
            # exp(-i theta/2 Z_a Z_b): Clifford iff theta is a multiple of pi/2
            theta = ev.params[0]
            a, b = ev.wires
            if _is_multiple_of_half_pi(theta):
                n_clifford += 1
                if round(theta / HALF_PI) % 4 in (1, 3):
                    # sqrt(CZ)-like; symplectically equivalent to CZ conjugation
                    frame.apply_cz(a, b)
            else:
                record_rotation(Frame._xor(frame.conj_z(a), frame.conj_z(b)))
        elif ev.gate == "u":
            theta, phi, lam = ev.params
            q = ev.wires[0]
            # U3 = Rz(phi) Ry(theta) Rz(lam); process in application order
            for angle, kind in ((lam, "z"), (theta, "y"), (phi, "z")):
                if abs(angle) < 1e-12:
                    continue
                if _is_multiple_of_half_pi(angle):
                    n_clifford += 1
                    k = round(angle / HALF_PI) % 4
                    if kind == "z":
                        for _ in range(k):
                            frame.apply_s(q)
                    else:  # Ry(k pi/2): odd k acts as X<->Z symplectically
                        if k % 2 == 1:
                            frame.apply_h(q)
                else:
                    record_rotation(frame.conj_z(q) if kind == "z" else frame.conj_y(q))
        else:
            raise SystemExit(f"unsupported gate for CAMPS analysis: {ev.gate}")

        if idx % sample_every == 0:
            profile.append({"event": idx,
                            "max_nu": max(min(cuts[j].rank, 2 * min(j + 1, n - j - 1))
                                          for j in range(n - 1)),
                            "nonclifford_so_far": n_nonclifford})

    # bond across cut k <= 2^min(nu_k, min(|left|,|right|))
    ranks = [min(cuts[k].rank, 2 * min(k + 1, n - k - 1)) for k in range(n - 1)]
    raw_ranks = [c.rank for c in cuts]
    profile.append({"event": len(circuit.events), "max_nu": max(ranks),
                    "nonclifford_so_far": n_nonclifford})
    return {
        "circuit": path.name,
        "n_qubits": n,
        "n_events": len(circuit.events),
        "clifford_ops": n_clifford,
        "nonclifford_rotations": n_nonclifford,
        "clifford_fraction": n_clifford / (n_clifford + n_nonclifford),
        "max_nu": max(ranks),
        "mean_nu": sum(ranks) / len(ranks),
        "nu_per_cut": ranks,
        "nu_raw_per_cut": raw_ranks,
        "nu_at_middle_cut": ranks[(n - 1) // 2],
        "implied_max_bond_log2": max(ranks),
        "profile": profile,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--sample-every", type=int, default=250)
    args = ap.parse_args()
    results = []
    for q in args.qasm:
        r = analyse(q, args.sample_every)
        results.append(r)
        print(f"{r['circuit']}: n={r['n_qubits']} clifford={r['clifford_fraction']:.1%} "
              f"nonclifford_rot={r['nonclifford_rotations']} "
              f"max_nu={r['max_nu']} (bond <= 2^{r['max_nu']})")
    if args.out:
        args.out.write_text(json.dumps({"schema": "camps-nullity-v1",
                                        "answer_blind": True,
                                        "results": results}, indent=2))


if __name__ == "__main__":
    main()
