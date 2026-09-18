# BlueQubit P1 v2 Mac portfolio report

Status: `CURRENT_METHODS_EXHAUSTED` for the tested blind portfolio. This is not
a claim that the challenge circuit is mathematically unsolvable. It means that
the bounded methods tested here did not produce a converged candidate on the
Apple M3 Pro.

## Provenance and scope

The branch is `bluequbit-p1-mac-portfolio`, created from v1 head
`efd24d3e3d46f2f038d3bfddd7bfa09a50a52bd2`. The local input is
`/Users/monitsharma/Downloads/P1_little_dimple.qasm`, SHA256
`0a02afffbdcf6755d5ed16b3a10cddd40cde4ee072d6072dbe7013e1c42f2ff8`, size
219,814 bytes. The P1 answer remained blind. No P9, P11, P12, HPC, cloud,
QPU, hardware, or answer lookup was performed in v2.

The Mac has arm64 macOS 26.5.2 and 36,864 MiB nominal unified memory. The
portfolio Python environment has NumPy 2.2.6, SciPy 1.15.3, Qiskit 1.4.5,
Quimb 1.15.0, and the existing qstvec checkout is pinned locally at commit
`545614fa196e2a77d96d408e0cdf39520684b251`. Julia PPS dependencies were
instantiated in the existing `julia/pps` project.

## 1. P1 computational structure

The input-only profiler confirms 36 qubits, 4,407 gates, 2,950 arbitrary
single-qubit `U` gates, 1,457 `CZ` gates, depth 307, and two-qubit depth 153.
There are 564 unique interacting pairs; simple unweighted mean degree is
31.333, while weighted interaction frequency mean is 80.944. The latter is
not graph degree. The interaction graph is dense and connected. The temporal
and ordering proxies are in the v1 forensic artifacts and the v2 profile.

The new Clifford audit finds only 1.05% of U gates within phase-invariant
distance `1e-6` of a single-qubit Clifford and 1.46% within `1e-2`. Decision:
`CLIFFORD_PERTURBATION_LOW_PRIORITY`. A large stabilizer-rank attack is not
justified by this measurement.

Backward lightcones span the circuit for every output. The algorithmic initial
PPS panel is qubits `[5, 15, 23, 0, 8, 27, 35, 17]` (zero-based), selected from
lightcone complexity rather than approximate answer bits.

## 2. Exact compilation

Qiskit transpilation at optimization levels 1, 2, and 3 with the exact
`u,cz` basis leaves all metrics unchanged: 4,407 gates, 2,950 U, 1,457 CZ,
depth 307, and two-qubit depth 153. No approximate synthesis was used. The
decision is `NO_MATERIAL_EXACT_QISKIT_SIMPLIFICATION`.

## 3. Sparse statevector attack

The local adapter uses complex128 by default, an in-place specialized CZ phase
kernel, a vectorized two-output U update, pre-renormalization discarded-mass
accounting, and a 28-GiB/120-second Mac guard. The completed original-order
instruction ladder was:

| top-k | time | peak RSS | top-1 probability after renormalization | discarded-mass proxy |
|---:|---:|---:|---:|---:|
| 4,096 | 2.62 s | 72.3 MiB | 0.00626 | 252.93 |
| 16,384 | 11.28 s | 77.2 MiB | 0.00996 | 235.32 |
| 65,536 | 50.30 s | 90.4 MiB | 0.00201 | 209.70 |
| 262,144 | >120 s | 168.6 MiB observed | unavailable | unavailable |

The top-1 string changed at every completed rung and top-5 Jaccard overlap was
0.0 between adjacent completed rungs. The instruction-level sparse method is
therefore `REJECTED_UNCONVERGED`; renormalized probabilities are not estimates
of true circuit probabilities.

The qstvec-style dependency-ready block scheduler was then implemented with
exact local block matrices and checked against sequential evolution on a small
fixture. Its valid P1 runs also failed to converge:

| blocks | top-k | priority | time | discarded-mass proxy | top-1 |
|---:|---:|---|---:|---:|---|
| 1,428 | 4,096 | CZ-first | 2.31 s | 258.79 | `010011000101110001111111001110101011` |
| 819 | 4,096 | CZ-first | 2.15 s | 218.27 | `111100100011011010001000101000000101` |
| 1,428 | 16,384 | CZ-first | 9.87 s | 229.00 | `100100101101111110100001101111100110` |
| 1,428 | 65,536 | CZ-first | 44.43 s | 199.859 | `001000000111001101000101011111011110` |
| 819 | 65,536 | CZ-first | 41.84 s | 187.74 | `101101000011100000110001111011000011` |
| 823 | 65,536 | U-first | 8.85 s | 182.999 | `010001101010000001011110000010110101` |
| 1,428 | 65,536 | CZ-first, p=0.99 | 56.52 s | 204.455 | `100111101101011001111000100010000001` |

The block top-1 changes across all tested footprints and the independent legal
priority. These runs are `REJECTED_UNCONVERGED`. An earlier pre-fix block
artifact is preserved as `blocks_k262144_q3_invalid_pre_fix.json` and excluded
from evidence because its embedding incorrectly cleared untouched local bits.
The corrected 262,144-support run reached 2,711/4,407 events in 120 s before
the wall guard, with discarded-mass proxy 101.62; it produced no promotion
evidence.

As an independent control, the pinned public qstvec `sharp_peak.py` block
construction was run blind on the same QASM. It completed all 1,427 blocks at
both supports: 12.74 s and top-1
`001110000111110111000100000111101100` at `k=16,384`, then 56.56 s and
top-1 `001001111000110000100010001111001001` at `k=65,536`. The top-1 change
rejects convergence for this implementation as well; the renormalized peak
probabilities (`0.00172` and `0.00146`) are not true circuit probabilities.

## 4. Specialized CZ kernel

On 100 P1 CZ operations over a 65,536-state support, the in-place kernel took
0.0108 s versus 1.176 s for generic qstvec CZ evolution: 108.5× measured
speedup, zero maximum absolute error, and exact support preservation. This is
a real implementation improvement, but it does not solve support growth from
the U gates.

## 5. PPS

The P1 adapter was validated on an exact two-qubit U+CZ fixture against Qiskit;
the Z expectation matched to approximately `1e-16`. The blind eight-output
panel was run at thresholds `1e-2`, `5e-3`, `2.5e-3`, and `1.25e-3`. Every
threshold produced zero surviving terms and zero expectations for all eight
observables. PPS was stopped at the smoke gate and classified
`REJECTED_PPS_SMOKE_ZERO_TERMS`; no P1 bits are promoted by PPS.

## 6. BP

Quimb `contract_d1bp` built a 5,900-tensor network with 7,357 open indices but
failed during its bounded 20-iteration feasibility probe with a missing-message
`KeyError` before convergence. No marginals or conditional greedy candidate
were produced. Decision: `REJECTED_FEASIBILITY`; D2BP and conditional decoding
were not justified.

## 7. Existing MPS as a weak signal

The prior v1 Fiedler/lookahead MPS output was included only as a secondary weak
vote. It is not treated as a correctness result: its cross-seed P1 evidence was
unstable and the same method failed the v1 P9 control. Consensus therefore does
not allow MPS to dominate the new methods.

## 8. Fixed-output amplitude contraction

For the `k=65536` sparse top-1 candidate, Quimb/Cotengra path rehearsal did not
return a contraction path or estimate within a 120-second wall guard and
spawned multiple path-search workers. Decision: `AMPLITUDE_VERIFIER_NO_GO`;
no Hamming-neighborhood scan was attempted.

## 9. Public mirrored-TNO feasibility probe

The public peaked-circuit TNO construction was adapted to a bounded numpy/Quimb
CPU runner with a single-process greedy contraction path. The exact two-qubit
fixture completed successfully. On P1, a bond-2/cutoff-0.5/chunk-1 diagnostic
completed in 3.28 s at 249 MiB RSS and decoded
`010101001100101110110010111001011101`; this is explicitly low-bond diagnostic
evidence, not a solution. A bond-4/cutoff-0.1/chunk-1 run consumed about 0.87 GB
RSS and remained inside its first compression call for 133 s, beyond the
120-second method budget; it was terminated by the external wall watchdog and
produced no candidate. Decision: `REJECTED_TNO_CPU_FEASIBILITY` for this Mac
configuration. The public reference method targets circuits without hidden
permutations; P1 did not show a direct mirrored gate match, so this is a
method-fit result, not a claim that TNO is mathematically impossible.

## 10. Public CircuitPermMPS bitstring distillation

The public distillation workflow was adapted with its two-step final qubit
mapping, then validated on the exact two-qubit fixture. Bond-64 complex128 P1
runs used 1,000 samples at seeds 1234 and 5678, followed by 10,000 samples at
both seeds. The two 10,000-sample votes differed by only 2 of 36 bits, but the
vote still had weak margins on many positions and no voted string appeared in
the sample set. The 10,000-sample runs took 95.06 s and 96.17 s at about
220--223 MiB RSS. A correctly typed bond-128 complex128 run completed in
192.37 s at 276 MiB RSS, but its vote differed materially from bond-64. The
bond-128 complex64 run instead failed with NaN sampling probabilities after
100.72 s. A sequential conditional-norm greedy decoder also produced three
different candidates at bonds 16, 32, and 64. Decision:
`REJECTED_MPS_NONCONVERGENCE_AND_COMPLEX64_NUMERICAL_INSTABILITY`; this is
useful partial evidence, not a solved P1 output.

Replacing hard rank truncation with probability-mass retention did not help:
at `top_k=65536`, `p_frac=0.999` and `0.9999` produced different top strings
after 61.07 s and 61.28 s, respectively. Decision:
`REJECTED_MASS_RETENTION_NONCONVERGENCE`.

## 11. Sparse-Pauli and randomized PPS follow-up

To test whether the zero-term Julia PPS result was only a representation
artifact, the public SPD sparse-Pauli representation was independently
validated on the exact fixtures using the same U/CZ decomposition. On P1
observable q5, thresholds `0.01`, `0.005`, and `0.001` all returned zero
expectation and zero retained terms in 0.57--6.56 s. A lower-threshold
`1e-4` probe ran for about 36 minutes and reached approximately 10.7 GB RSS
without returning a value; it was stopped by the external watchdog. The
PauliPropagation `mcpropagate` path was also tested with a 4,096-term cap and
reached approximately 18.6 GB RSS for one observable without returning. The
decisions are `REJECTED_SPD_NO_SIGNAL_AND_LOWER_THRESHOLD_INFEASIBLE` and
`REJECTED_RANDOMIZED_PPS_MEMORY_FEASIBILITY`. Neither path provides a bit to
promote. A separate 4,096-walker `mcsample` path completed in 2.71 s at
approximately 508 MiB RSS, but produced no final all-I/Z observable term and
therefore a zero estimate for q5. This is a bounded diagnostic, not evidence
that every output bit is zero; its decision is
`REJECTED_NO_OBSERVABLE_SUPPORT_IN_SAMPLE`.

## 12. Final P1-specific particle/resampling probe

As a distinct alternative to deterministic rank truncation, a fixed-particle
state-vector ensemble was implemented with exact CZ phase updates and
squared-amplitude resampling with unbiased reweighting. The 4,096-particle
P1 run advanced through 2,679 of 4,407 events in 1.10 s, then encountered
nonfinite weights from variance growth; no candidate was emitted. Decision:
`REJECTED_NUMERICAL_WEIGHT_OVERFLOW`. This method is not promoted.

## 13. MPS coordinate-ascent mode search

To use correlations more directly than independent sampling, eight bond-64
complex128 samples were used as starts for repeated single-bit amplitude
improvements on the bounded MPS. All eight starts reached different local
modes, despite the same circuit, cutoff, and bond. Decision:
`REJECTED_MPS_LOCAL_MODE_NONCONVERGENCE`.

## 14. Cross-method consensus

The blind consensus artifact compares completed instruction-level, block, and
exact-public-qstvec sparse top-1 strings with weak MPS and public-distillation
strings. It classifies 0 bits as strongly
supported, 0 as weakly supported, and 36 as unresolved. These are evidence classes, not correctness
claims. No `FINAL_CANDIDATE.json` is written because there is no serious
converged candidate to report.

## 15. Final timing and decision

No defensible final P1 solve path within the 7,200-second target was measured.
Individual sparse rungs fit within that budget but do not converge; the next
rung timed out at 120 seconds, PPS has no signal, BP is infeasible in the
tested representation, and amplitude verification is not practical under the
Mac path-search guard.

A separate greedy-path rehearsal completed in 1.03 s and returned width 60,
peak intermediate size `1.3150510911921855e18` elements, and approximately
`2.47e24` FLOPs. Attempting the corresponding contraction reached 19.49 GB
RSS after 62.26 s without returning. This is an explicit
`AMPLITUDE_VERIFIER_NO_GO_GREEDY_WIDTH_60` gate, not merely a path-search
timeout.

The v2 decision is `CURRENT_METHODS_EXHAUSTED`, not `SOLVED_WITH_STRONG_BLIND_EVIDENCE`.
The strongest positive finding is the 108.5× specialized-CZ speedup. The
strongest negative finding is method-independent failure to obtain converged
candidate evidence: instruction-level and mass-retention sparse instability,
zero-term PPS zero signal, SPD/randomized-PPS/path-sampling infeasibility or
no support, BP feasibility failure, TNO CPU infeasibility, MPS
bond/cutoff/dtype/decoder nonconvergence, and amplitude-path timeout.

Artifacts are under `results/bluequbit_p1_v2/`; the machine-readable state is
`results/bluequbit_p1_v2/RESEARCH_STATE.json`. The appropriate next action is a
new P1-specific algorithmic method, not more bond/cutoff/precision sweeps and
not HPC or challenge submission of the current candidate pool.
