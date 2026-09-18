#!/usr/bin/env python3
"""Observable-first simulation by sparse Pauli propagation (Heisenberg picture).

Computes <0| U^dag O U |0> for O = Z_i and Z_i Z_j without ever building the
state.  Motivation: P6's *state* decorrelates from the circuit under truncation
(P6_MPO_DIAGNOSIS.md section 9), but the peak only needs observables.  Whether
U^dag O U stays sparse in the Pauli basis is a different question from whether
the state is representable, so this is independent evidence -- unlike CAMPS,
whose nullity saturated on all four circuits.

Representation: a Pauli term is (x_mask, z_mask) with the Hermitian convention
P = i^{|x&z|} X^x Z^z, carried with a complex coefficient in a dict.

Propagation walks the circuit in reverse, mapping O -> G^dag O G:
  * CZ is Clifford, so each term maps to exactly one term.
  * U3 is not, so a term with a non-identity Pauli on that qubit maps to a
    combination of up to three terms, via the SO(3) Bloch matrix of the gate.

Truncation drops terms below `--threshold` and keeps at most `--max-terms` by
magnitude.  Finally <0|P|0> = 1 for I/Z-only strings and 0 otherwise, so the
expectation is the sum of coefficients over terms with x_mask == 0.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from structural.qasm_events import parse_qasm

I2 = np.eye(2, dtype=complex)
SX = np.array([[0, 1], [1, 0]], dtype=complex)
SY = np.array([[0, -1j], [1j, 0]], dtype=complex)
SZ = np.array([[1, 0], [0, -1]], dtype=complex)
SIG = (SX, SY, SZ)


def u3_matrix(theta: float, phi: float, lam: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array([[c, -np.exp(1j * lam) * s],
                     [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]], dtype=complex)


def bloch_conj(g: np.ndarray) -> np.ndarray:
    """M with  g^dag sigma_b g = sum_a M[a,b] sigma_a  (real orthogonal)."""
    gd = g.conj().T
    m = np.zeros((3, 3))
    for b in range(3):
        t = gd @ SIG[b] @ g
        for a in range(3):
            m[a, b] = (0.5 * np.trace(SIG[a] @ t)).real
    return m


# local Pauli label from (x,z) bit pair: 0=I, 1=X, 2=Y, 3=Z
_LABEL = {(0, 0): 0, (1, 0): 1, (1, 1): 2, (0, 1): 3}
_BITS = {0: (0, 0), 1: (1, 0), 2: (1, 1), 3: (0, 1)}
# phase bookkeeping: our convention P = i^{|x&z|} X^x Z^z makes Y = i X Z, which
# is exactly SY, so the label<->matrix map needs no extra phase.


def propagate(circuit, obs_qubits, threshold: float, max_terms: int):
    n = circuit.n_qubits
    x0 = 0
    z0 = 0
    for q in obs_qubits:
        z0 |= 1 << q
    terms = {(x0, z0): 1.0 + 0j}

    # precompute Bloch matrices for u3 gates
    dropped_weight = 0.0
    max_seen = 1
    for ev in reversed(circuit.events):
        if ev.gate == "cz":
            a, b = ev.wires
            new = {}
            for (x, z), c in terms.items():
                xa = (x >> a) & 1
                xb = (x >> b) & 1
                # CZ: X_a -> X_a Z_b, X_b -> X_b Z_a; Z unchanged.
                nz = z
                if xa:
                    nz ^= 1 << b
                if xb:
                    nz ^= 1 << a
                # When both sites are X-type the two appended Z's must be
                # commuted back past the local operators; in the
                # P = i^|x&z| X^x Z^z convention that leaves a -1 exactly when
                # one site is Y and the other is X.
                if xa and xb and (((z >> a) & 1) ^ ((z >> b) & 1)):
                    c = -c
                key = (x, nz)
                new[key] = new.get(key, 0j) + c
            terms = new
        elif ev.gate == "u":
            q = ev.wires[0]
            m = bloch_conj(u3_matrix(*ev.params))
            new = {}
            qx = 1 << q
            for (x, z), c in terms.items():
                lab = _LABEL[((x >> q) & 1, (z >> q) & 1)]
                if lab == 0:
                    new[(x, z)] = new.get((x, z), 0j) + c
                    continue
                col = lab - 1
                bx = x & ~qx
                bz = z & ~qx
                for a in range(3):
                    coef = m[a, col]
                    if coef == 0.0:
                        continue
                    ax, az = _BITS[a + 1]
                    key = (bx | (ax << q), bz | (az << q))
                    new[key] = new.get(key, 0j) + c * coef
            terms = new
        else:
            raise SystemExit(f"unsupported gate: {ev.gate}")

        # truncate
        if threshold > 0 or (max_terms and len(terms) > max_terms):
            items = [(k, v) for k, v in terms.items() if abs(v) >= threshold]
            dropped_weight += sum(abs(v) ** 2 for k, v in terms.items() if abs(v) < threshold)
            if max_terms and len(items) > max_terms:
                items.sort(key=lambda kv: -abs(kv[1]))
                dropped_weight += sum(abs(v) ** 2 for _, v in items[max_terms:])
                items = items[:max_terms]
            terms = dict(items)
        max_seen = max(max_seen, len(terms))

    value = sum(c for (x, z), c in terms.items() if x == 0).real
    return value, {"max_terms_seen": max_seen, "final_terms": len(terms),
                   "dropped_weight": dropped_weight}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("--threshold", type=float, default=1e-8)
    ap.add_argument("--max-terms", type=int, default=200000)
    ap.add_argument("--single", action="store_true", help="only <Z_i>")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    circuit = parse_qasm(args.qasm)
    n = circuit.n_qubits
    t0 = time.time()
    singles, stats = [], []
    for i in range(n):
        v, st = propagate(circuit, [i], args.threshold, args.max_terms)
        singles.append(v)
        stats.append(st)
        print(f"  <Z_{i:2d}> = {v:+.6f}   terms_max={st['max_terms_seen']:>8d} "
              f"dropped={st['dropped_weight']:.2e}", flush=True)
    payload = {"schema": "pauli-propagation-v1", "answer_blind": True,
               "circuit": args.qasm.name, "n_qubits": n,
               "threshold": args.threshold, "max_terms": args.max_terms,
               "single_z": singles, "stats": stats,
               "wall_seconds": time.time() - t0}
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2))
    print(f"\n  wall {payload['wall_seconds']:.1f}s")


if __name__ == "__main__":
    main()
