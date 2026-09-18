# Pauli propagation for P5/P6 — closed by the positive control

**Verdict: closed.** The Pauli support of `U^dag Z_0 U` explodes on **P5, a circuit
already solved**, at 7.7% of the circuit. A method that cannot compute a single
observable on a solved control cannot be trusted on P6.

## Why it was worth trying

It asks a genuinely different question from everything else attempted. CAMPS
asks "is the *state* representable" and saturated on all four circuits
(`P6_CAMPS_FEASIBILITY.md`). Pauli propagation asks "is `U^dag Z_i U`
compressible *in Pauli space*", which can be easy even when the state is
maximally entangled. It also sidesteps P6's specific failure mode: the
approximate state decorrelates from the circuit under truncation
(`P6_MPO_DIAGNOSIS.md` section 9), and an observable-first method never builds
that state.

The plan was: compute `<Z_i>` and `<Z_i Z_j>` over the interaction edges, fit a
maximum-entropy Ising model, and take its MAP configuration -- turning the
simulation into observable estimation plus a 62-variable classical optimisation.

## Implementation and validation

`scripts/pauli_propagation.py`. Terms are `(x_mask, z_mask)` with the Hermitian
convention `P = i^|x&z| X^x Z^z`; the circuit is walked in reverse mapping
`O -> G^dag O G`. CZ is Clifford (one term in, one out); U3 is not, so a term
branches into up to three via the gate's SO(3) Bloch matrix.

**A sign bug was found and fixed during validation.** The first version passed
depth-2 circuits exactly and failed at depth 3. Unit-testing the conjugation
rules against explicit matrices localised it: the CZ rule dropped a `-1` in 2 of
16 two-qubit Pauli cases. When both sites are X-type, CZ appends a Z to each, and
commuting those back past the local operators leaves a sign exactly when one site
is Y and the other X. The wrong values looked plausible (-0.604 vs -0.559), which
is precisely how such a bug produces a confident wrong answer.

After the fix: all 16 two-qubit Paulis exact against explicit matrices, and 16/16
statevector comparisons exact to 1e-9 across n=4-7, depth 2-3, truncation off.

## Result

Support size for `<Z_0>`, threshold 1e-8, cap 2e6:

| events processed | P5 (solved, 5720 total) | P6 (10486 total) |
|---:|---:|---:|
| 50 | 1 | 7 |
| 100 | 1 | 154 |
| 200 | 1 | 154 |
| 400 | **44,685** | 1,314 |
| 800 | -- | **46,880** |
| **cap 2,000,000 exceeded at** | **event 440 (7.7%)** | **event 1270 (12.1%)** |

Growth is faster than exponential in the take-off region: P5 goes 1 -> 44,685 in
200 events, then to 2,000,000 in 40 more.

## Why the premise failed

`U^dag Z_i U` stays sparse only for shallow or heavily Clifford circuits. P5 has
3,828 arbitrary U3 gates, each branching a Pauli term into up to three. No
truncation threshold that preserves accuracy keeps that bounded -- surviving to
the end of P5 would require discarding essentially all the weight.

Note P6 survives *further in relative terms* than P5. The route does not fail
because P6 is special; it fails for the whole circuit family.

## Caveat

This measures the naive sparse-Pauli scheme. Production implementations use
Pauli-path truncation, coefficient-weighted merging and related refinements that
would push the wall further out. But "further" would need to mean 13x on P5 and
8x on P6 merely to reach the end of the circuit, against super-exponential
growth. That gap does not look closable by implementation quality.

## Artifacts

`scripts/pauli_propagation.py`, `results/pauli_propagation/p5_p6_support_growth.json`.
