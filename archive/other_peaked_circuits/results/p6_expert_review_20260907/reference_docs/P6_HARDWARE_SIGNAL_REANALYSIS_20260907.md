# P6 Helios-1 500-shot reanalysis: why no peak, and what would change it

Date: 2026-09-07. Offline reanalysis of the five corrected P6 batches
(500 shots, ~4,280 HQC). No provider calls, no HQC spent, no hidden-target
lookup for P6. P11/P12 accepted answers were used only as positive controls of
the decoders. Reproduce with `PYTHONPATH=src .venv/bin/python tools/p6_signal_reanalysis.py`
(outputs in `results/hardware/p6_signal_reanalysis_20260907/`).

## 1. The pipeline is not the problem

- Every one of the 500 raw frames carries 62 distinct `m###` labels in one
  fixed order; label-sorted reconstruction reproduces the saved shot arrays
  exactly. Framing and bit order are not hiding a peak.
- The frozen QASM reproduces the submitted bitcode byte for byte (chunk audit).
- The provider billed 856 HQC per 100 shots, which matches 3,494 two-qubit
  gates and ~7,000 single-qubit gates: the device executed the circuit as shipped.

## 2. The 500 shots are not uniform, but the signal is thin

Blind statistics against a uniform 500×62 null:

| statistic | P6 observed | uniform null |
|---|---:|---:|
| bit positions with marginal \|z\| > 3 | 17 of 62 | max ≈ 3 |
| per-batch bias-vector correlation (5 independent jobs) | 0.43–0.71 | ≈ 0 |
| shot pairs within Hamming 15 | 18 | ≈ 4 |
| largest connected component at Hamming ≤ 15 | 14 shots (batches 1,3,4,5) | 2–3 |
| shots agreeing ≥ 44/62 with the mixture centre | 23 | 2.7 |
| leading eigenvalue of the bit correlation matrix | 2.17 | 1.70–1.80 |

The non-cloud P6 shots (posterior < 0.5) are close to uniform (3 bits with
\|z\| > 3 out of 62 at n = 421), and the same is true for the non-cloud P11/P12
shots, so the structure is circuit-derived, not a per-ion readout or leakage
systematic. (Helios does show a small global excess of ones, +1.3–1.8 %, in all
three datasets; it is irrelevant to decoding.)

What the cloud looks like, compared with the runs that worked:

| | P11 (51 shots) | P12 (200 shots) | P6 (500 shots) |
|---|---:|---:|---:|
| 2q gates / per qubit | 1,999 / 41 | 2,457 / 50 | 3,494 / 113 |
| exact hits of the answer | 1 | 3 | 0 (no repeats at all) |
| shots within 15 bits of the answer/centre | 10 (20 %) | 7 (3.5 %) | ~20–25 (4–5 %) |
| per-bit fidelity of cloud shots (mixture q) | 0.86 | 0.88 | ≈ 0.70 |

P6 has a cloud of similar size to P12's, but its members are far less faithful:
no P6 shot agrees with the centre on more than ~52 of 62 bits. That is exactly
the regime where the frequency/medoid decoders that worked for P11/P12 fail.

## 3. This is what P11/P12 predicted

From the P11/P12 exact-hit rates (1/51, 3/200) the effective all-in error rate
on Helios is λ ≈ 3.9–4.2 errors per shot, i.e. ≈ 1.7–2.0 × 10⁻³ per CZ
including memory/transport, single-qubit and SPAM error. Applied to P6's
3,494 CZ: λ ≈ 6.6, per-shot exact-peak probability ≈ 0.14 %, ≈ 0.7 exact hits
expected in 500 shots. Zero was observed. The P6 result is therefore consistent
with the P11/P12 device performance; it is a noise-budget problem, not a
defect, and simply adding shots of the same circuit is the most expensive way
to fix it (≈ 8.6 HQC/shot, a few exact hits per 1,000 shots).

## 4. Decoders

Two target-blind decoders were run, each validated on P11/P12 first.

**Independent-bit mixture (EM).** Product-Bernoulli cloud around x with per-bit
q plus a uniform component. Recovers P11 (51 shots) and P12 (200 shots)
exactly; a 100-shot P12 subsample gives 5 wrong bits. On P6 the log-likelihood
gain (268 nats) barely exceeds a null with independent bits at P6's own
marginals (219–265 nats): most of the gain is marginal bias, not clustering.

**Light-cone mixture (LC-EM).** Peak x plus one late error that scrambles
exactly one forward light cone; cones are computed from the QASM gate order
(P6: 129 distinct partial cones, 13 % of gate positions). Recovers P11 from
51 shots and P12 from 200 or 100 shots exactly, and from 50 shots in some
random draws. On P6: gain 63 nats (nulls 16–30), so real structure, but the
optimum depends on the starting point (two fixed points 8 bits apart), the
cold bootstrap median distance to the full-data optimum is 9–10 bits, and the
batches 1–3 vs 4–5 split disagrees on 12 bits. **No P6 string is promoted.**

Post-hoc only: neither P6 decoder output is meaningfully consistent or
inconsistent with the 13 previously scored candidates (predicted-vs-actual
overlap correlation +0.10; random strings give 0.0 ± 0.35). The scores were
not used to construct or select anything.

## 5. What was left on the table: the circuit was never 2q-optimised

The submitted QIR is a plain rebase to {Rz, Rx, Ry, CZ, X}. An offline pytket
pass (`FullPeepholeOptimise(allow_swaps=False, target_2qb_gate=TK2)`, 46 s)
reduces P6 to 2,593 two-qubit blocks: 1,981 single-coordinate (CZ-class),
318 two-coordinate, 163 three-coordinate, and 184 identity patches that were
being executed for nothing. Minimal ZZ-equivalent count is 3,106; a
fidelity-aware `DecomposeTK2` to native `ZZPhase` yields 2,909 gates, 592 of
them with |angle| < π/4. Under a linear-in-angle error model the expected
circuit survival rises from 0.061 to 0.152 (~2.5×) and HQC drops ~17 %
(≈ 6.9 vs 8.6 HQC/shot). The provider does not do this for QIR input.

## 6. Recommended path

1. **Resubmit the optimised circuit, not the shipped QIR.** Compile with pytket
   (`FullPeepholeOptimise` → fidelity-aware `DecomposeTK2`/`ZZPhase`), verify
   `implicit_qubit_permutation()` is the identity, keep the `m###` measurement
   registers, and confirm the HQC quote falls to ≈ 690–700 per 100 shots.
2. **Pre-register a cheap, decisive test before spending more.** Freeze the
   current LC-EM centre. In a 200-shot optimised run count shots agreeing with
   it on ≥ 44/62 bits: uniform null ≈ 1, the current device performance predicts
   ≈ 9, a 2.5× fidelity gain predicts ≈ 20–45. Also count exact repeats.
3. **Decode pooled data with the light-cone EM,** then confirm on a held-out
   batch exactly as the P12 protocol did. The P6 cloud needs roughly 3–4×
   more effective members than it has now to pin all 62 bits; 500 optimised
   shots pooled with the existing 500 should get there if step 2 confirms
   the fidelity gain (≈ 3,500 HQC).
4. Do not spend more HQC on the unoptimised circuit, and do not submit any of
   the current P6 strings as an answer.

The classical route is not closed either: the original GPU MPO-unswap solver
(A100, χ 4096–8192) has never been run on P6, and the same pytket pass removes
the 184 identity patches that every classical run so far simulated.
