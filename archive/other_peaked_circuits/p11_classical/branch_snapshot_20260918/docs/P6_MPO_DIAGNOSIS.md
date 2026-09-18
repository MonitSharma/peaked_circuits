# P6 MPO diagnosis — no verified peak; cutoff transition unresolved

> **STATUS UPDATE 2026-09-01.** P6 has now completed at both cutoff 2e-3 and
> 1.875e-3, but both completed routes are flat and produce no candidate. The
> tighter 1.875e-3 run reached 2593/2593 with 1000/1000 unique samples and
> sample peak fraction 0.001. New D128 permutation-MPS, loose-extraction,
> structural, and overnight checks also produced no verified answer. Current label:
> **`NONCONVERGED — no candidate; cutoff interval partially probed`**.
> See [PEAKED_FIDELITY_CALIBRATION.md](PEAKED_FIDELITY_CALIBRATION.md) and the
> [2026-08-31 reassessment](P6_P8_REASSESSMENT_20260831.md).


**Circuit:** `P6_titan_pinnacle.qasm` — 62 qubits, depth 416, 3,494 CZ + 6,992 U3,
consolidating to **2,593 work gates**. SHA256
`206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4`.

**Solver:** `d-kremer`-style midpoint MPO + greedy unswapping + SABRE routing
(`p9solver`, commit `b1bed0a`), run via `scripts/run_p11_mpo.py`.
**Environment:** conda `p9-openblas` (Python 3.10.21, SciPy 1.15.2). The
`.venv-p9-isolated` environment (Python 3.10.16, SciPy 1.15.3) **segfaults** at
D=512 and must not be used.

No target answer or portal score was read during candidate generation.

---

## 0. Calibration reference

Two anchors bound what counts as a real answer:

| control | peak fraction | decoder top-1 prob | outcome |
|---|---|---|---|
| P9 (5 runs, D=512, cutoff 6e-4) | 0.036–0.096 | 5.3e-2 | correct |
| **P5** (D=512, cutoff 6e-4, bond_profile) | **0.012** | **1.09e-2** | **correct, 44/44** |
| P9 loose control (D=512, cutoff **5e-3**) | 0.001 | 4.9e-9 | wrong (Hamming 25/56) |

P5 is the important one: it establishes that a **1.2% peak is sufficient**, so
the bar is a *distinct* mode (top-1 clearly beating top-2), not a large one.

---

## 1. Baseline P6 MPO runs (through 2026-08-30)

| tag | D | cutoff | route | sel-mode | guard | gates | term | wall |
|---|---|---|---|---|---|---|---|---|
| `p6_prefix100_abs` | 64 | 5e-3 | 1/none | bond | 3 | 100 | max_work_gates | 53 s |
| `p6_full_d128` | 128 | 5e-3 | 1/none | bond | 20 | **2593** | **completed** | 705 s |
| `p6_full_d128_decode` | 128 | 5e-3 | 1/none | bond | 20 | 2004 | killed (900 s wall) | 783 s |
| `p6_d512_c6e4` | 512 | 6e-4 | 1/none | bond | 2 | 86 | no_progress | 423 s |
| `p6_d512_c6e4_noprogress20` | 512 | 6e-4 | 1/none | bond | 20 | 102 | killed | 721 s |
| `p6_d512_c6e4_no_progress_guard` | 512 | 6e-4 | 1/none | bond | −1 | 35 | killed | 133 s |
| `p6_d512_bondprofile` | 512 | 6e-4 | 4/bond_profile | bond | 60 | 138 | killed (stalled) | 4284 s |
| `p6_hybrid_overnight` | 512 | 6e-4 | 1/none | bond_route_proxy hybrid | 60 | 107 | no_progress | 1915 s |
| `p6_d512_cut1e3` | 512 | 1e-3 | 4/bond_profile | bond | 60 | 180 | killed (stalled) | 6931 s |
| `p6_d512_cut2e3` | 512 | **2e-3** | 4/bond_profile | bond | 60 | **2593** | **completed** | 9436 s |

---

## 2. What was ruled out, and by what evidence

### 2.1 Not entanglement-limited

`selected_absorbs_hit_max_bond = 0` on **every** D=512 run. The bond cap was
never binding on an absorption. `p6_d512_bondprofile` and `p6_d512_cut1e3` both
touched bond 512, but only transiently during *unswapping* (1 row), never during
absorption. Raising D is not the fix.

### 2.2 Not element-threshold-limited

No run was ever blocked by `unswap_threshold`. Probe rejections were a small
minority (30 left / 42 right out of 998 absorb rows on the bond_profile run).

### 2.3 Routing-limited, at low bond

The work split is the tell. On `p6_d512_bondprofile`: **3,426 unswapping rows
against 998 absorbing rows**, 109 unswap cycles, to move 138 gates. On
`p6_d512_cut1e3`: **4,398 unswapping vs 1,289 absorbing**, 145 cycles, 180 gates.
The router does 3–3.4× the absorber's work and converts almost none of it into
progress — the same signature `P11_ROUTING_DIAGNOSIS.md` §1 documents.

### 2.4 Route-aware machinery did not help

- `--route-score bond_profile` with 4 candidates: 138 gates (best at 6e-4).
- `bond_route_proxy` + `allow-nonbond` + `hybrid`: **107 gates** — worse.
- `--route-candidates 1` (cheaper router): 107 vs 138 — the speed/quality trade
  lost. Throughput doubled (2.9 → 6 gates/min) but progress fell.
- Guard relaxation (2 → 20 → 60 → −1) never unblocked anything at 6e-4.

---

## 3. The completion/fidelity conflict (main finding)

Cutoff, not bond or threshold, controls whether P6 completes:

| cutoff | gates reached | outcome |
|---|---|---|
| 6e-4 (P9-validated) | 86–138 / 2593 | router stalls |
| 1e-3 | 180 / 2593 | router stalls |
| **2e-3** | **2593 / 2593** | **completes — peak destroyed** |
| 5e-3 | 2593 / 2593 | completes (never sampled; certainly destroyed) |

Looser truncation keeps the MPO small, so absorbs stay cheap and the router
stops thrashing. But the completed 2e-3 run yields nothing:

```
sample_peak_fraction  0.001      (P5 correct: 0.012;  P9 failure control: 0.001)
sample_unique_raw     1000/1000  (all samples distinct)
decoder top-1 prob    2.8e-07    (P5 correct: 1.09e-2)
top-1 / top-2         1.02x      (P5 correct: 7.8x)
final sampling state  max_bond 4, total_elems 294
```

A 62-qubit state described by 294 numbers is structureless. The MPO peaked at
bond 510 / 1.24M elements — it did real work — but the truncation discarded the
peak along the way.

**On current evidence the two windows do not overlap:** every tolerance that
preserves the answer stalls the router, and every tolerance that finishes has
already thrown the answer away. The fidelity boundary is at or below 1e-3; the
completion boundary is at or above 2e-3.

### Candidate produced (DO NOT SUBMIT)

```
11000011111011111011011100000110110000100101001001000110110110
```

Classified **`NONCONVERGED` / no information**. Its diagnostics sit exactly on
the P9 known-failure control.

---

## 4. Historical gaps and current status

1. **The 1e-3 → 2e-3 gap is still incomplete.** The 1e-3 overnight stage and
   the 1.75e-3 probe did not reach a natural endpoint; the 2e-3 runs completed
   flat. A proper cutoff bisection remains open.
2. **Seed variation at 6e-4 remains untested on P6.** The D128 loose-cutoff
   seed comparison was unstable, but it does not answer the faithful-cutoff
   question.
3. **`pair_lookahead` is no longer untried.** P6 overnight stages B/C reached
   only 24/2593 work gates before wall/user stops, so the selector is not a
   practical rescue at the tested settings.

## 5. Status

`CURRENT_METHODS_EXHAUSTED` is **not** yet the right label. The accurate one is
**`NONCONVERGED — no candidate; completion/fidelity conflict characterised; cutoff window partially probed`**.


---

# 6. 2026-08-30 update — hypotheses tested and eliminated

## 6.1 What was run

| tag | cutoff | router | gates | outcome |
|---|---|---|---|---|
| `p6scr_flip2` | 6e-4 | `flip_freq=2`, 4/bond_profile | 148/2593 | killed (screen); **beat the 138 ceiling** |
| `p6scr_pairlook` | 6e-4 | `pair_lookahead` | 21/2593 in 48 min | **rejected** on throughput |
| `p6main_flip2_c15` | 1.5e-3 | `flip_freq=2` | 89/2593 | killed; 24 h ETA vs 12 h budget |
| **`p6main_c2e3_long`** | **2e-3** | **`flip_freq=2`** | **2593/2593 COMPLETED** | **flat — no signal** |

`--flip-freq` had to be exposed in the CLI first: `pipeline.py` has always
supported it (lines 1703, 1775) but `cli.py:829` hard-coded `flip_freq=None`.
Patched in worktree `peaked-mpo-solver-p6` (branch `p6-flipfreq`).

## 6.2 The completed run

```
2593/2593 gates, termination_reason: completed, left: 2, right: 2
peak_max_bond 510, peak_total_elems 1,107,380, final bond 27
sample_peak_fraction  0.001    (1000/1000 samples unique)
decoder top-1 prob    1.22e-08
top1/top2             1.06x
compress_time         9287 s
```

Candidate (**DO NOT SUBMIT — no information**):

```
10100100111000110010101011111001100010011010101111100111101010
```

This run was *healthy by every process metric*: balanced halves throughout
(L 449/1296, R 462/1297 at mid-run), zero aborts across 175 unswap cycles,
and it accelerated mid-circuit from 3.3 to 11.7 gates/min — the same second-half
speed-up P5 shows. It reached 6x further than any previous P6 attempt. **And it
still produced nothing.**

## 6.3 Four hypotheses eliminated

1. **Cutoff window** — *not* refuted; see §7. P9 recovers exactly at 6e-4,
   1.5e-3 *and* 2e-3, with its **best** mode at 1.5e-3 (top1/top2 = 23x), which
   shows loosening is not *inherently* destructive **for P9**. It does not show
   that P6 lacks its own transition inside 1.5e-3 < c < 2e-3.
2. **Depth** — refuted. P9 is 1885 work gates (73% of P6's 2593) and is exact at
   2e-3. Truncation error accumulating over 2593 gates does not explain P6.
3. **Materialized-state size as a fidelity meter** — refuted. P9 returned 56/56
   from a 174-element state, *smaller* than P6's destroyed 294.
4. **Route/trajectory quality** — refuted by the controlled test in §6.1: same
   circuit, same cutoff, only the router changed. `flip_freq=2` gave an equally
   flat result with a top-1 an order of magnitude worse than the default router.

## 6.4 Verdict

**`NONCONVERGED`** for the MPO route on P6 — no candidate, and the cutoff
interval is only partially probed (§7). This is weaker than the
`CURRENT_METHODS_EXHAUSTED` label an earlier revision of this document used.

P6 is not shown to be absorption-bond-limited (`selected_absorbs_hit_max_bond =
0` on every D=512 run), and the completed 2e-3 runs are flat under two very
different routers. That is consistent with a weaker or more delocalised P6 peak,
but it does not rule out a circuit-specific cutoff transition or an interaction
between routing and fidelity. The unresolved sub-2e-3 bisection is the reason
the current label remains `NONCONVERGED`.

Note this is a *different* failure from P8. P8 cannot finish; P6 finishes and
the answer is not there.

## 6.5 The one experiment that could still change this

**P6 at cutoff 1.5e-3 with `flip_freq=2`.** Earlier 1.5e-3 attempts stalled at
89-180/2593 under the tested budgets; none was run to a natural stall or
completion. P9's clean 1.5e-3 control keeps this as a useful calibration point,
not evidence that P6 will complete or retain its peak.

If that also completes flat, P6 is closed on this method.


---

# 7. Correction and the state of the cutoff question

## 7.1 What was overstated

An earlier revision of §6.3 asserted the cutoff-window hypothesis was
**refuted**. That was wrong, and the error is worth naming precisely: the
refutation rested on **P9 data, not P6 data**. P9 being exact at both 1.5e-3 and
2e-3 shows a looser cutoff is not inherently destructive *for P9*. It does not
establish that P6 lacks a circuit-specific transition inside that interval.

The two P6 endpoints actually measured are:

| cutoff | router | gates | outcome |
|---|---|---|---|
| 1.5e-3 | `flip_freq=2` | 89/2593 | **terminated for budget, not stalled** |
| 1.75e-3 | `flip_freq=2` | 164/2593 | **terminated by operator while decaying** |
| 2e-3 | `flip_freq=2` | 2593/2593 | completes, flat |
| 2e-3 | default `bond` | 2593/2593 | completes, flat |

Neither sub-2e-3 run was ever run to a stall or a completion. So the claim
"P6 cannot complete below 2e-3" is **unproven** — both runs were stopped by
scheduling decisions, not by the solver.

A window of the form `c_router < c* < c_fidelity` therefore remains possible.

## 7.2 What the 1.75e-3 probe did show

51 minutes of absorption, 164/2593 gates, zero aborts, `peak_max_bond` 512 but
`selected_absorbs_hit_max_bond = 0` (bond cap never binding, as on every other
P6 run). Progress in 20-minute buckets:

```
+120   +30   +1
```

Monotonic decay, in contrast to the 2e-3 run that completed, which was lumpy but
recovered from pauses and *accelerated* mid-circuit from 3.3 to 11.7 gates/min.
Suggestive that 1.75e-3 sits below the completion boundary, but **it is not a
stall observation** — the run was stopped deliberately.

## 7.3 One piece of evidence that argues the window is narrow or absent

At 2e-3, P6's mode is `top1/top2 = 1.02-1.06x` — *completely* flat. At the same
cutoff P5 gives 3.4x: degraded, but with a clear surviving mode. If P6 sat just
above a fidelity transition, partial degradation would be expected rather than
total collapse. This is consistent with P6's boundary lying well below 2e-3,
possibly below 1.5e-3 — though a sufficiently sharp transition would look the
same. It is an argument for bisecting **downward**, not a proof.

## 7.4 Prerequisite unblocked: structural analysis can now read P6

`structural/qasm_events.py` previously **raised** on the first gate line of P6
(`u3`) and P8 (`u3`/`iswap`), and `_QREG` hard-coded the register name `q`, so
P5 (`q83`) failed too. The entire structural stack -- mirror analysis, patch
unitaries, fingerprints, sequence matching -- had never been able to parse these
circuits. Fixed in `ffeb592`; all four circuits now parse with verified gate
counts (P5 44/1892, P6 62/3494, P8 40/888, P9 56/1917), with a regression test
and 202 passing tests.

This is a precondition for local-unitary / Weyl-invariant patch matching against
the HQAP construction, which is the natural next direction if the tensor route
stays closed.

## 7.5 Open experiments, in the order they are worth doing

1. **Complete the bisection properly** -- run 1.75e-3 (and if needed 1.875e-3 /
   1.625e-3) to an actual stall or completion, not to a scheduling decision.
2. **Adaptive cutoff ("rescue pulses")** -- base 1.5e-3, temporarily relaxed only
   where the router stalls, so the fidelity cost is paid locally rather than
   across all 2593 gates. Note `cutoff` is a scalar used in *both* the absorb
   probes and the unswap compressions; relaxing during absorption and relaxing
   during unswapping are different experiments and should be instrumented
   separately. Calibrate on P5 (44/44) and P9 (56/56) with pulses active
   *before* applying to P6.
3. **Structural deobfuscation** -- local-unitary invariants (Weyl/Cartan,
   Makhlin, operator-Schmidt) over maximal two-qubit patches, seeking
   `A ~ B†` under unknown local rotations and qubit permutation. Now unblocked
   by 7.4.

## 7.6 Post-hoc P6 bitstring reference set

The following eight 62-bit strings were supplied for post-hoc evaluation and
their overlaps with the correct P6 bitstring were reported externally. Keep
this table as a comparison set for future candidates. These scores are
evaluation anchors only: they must not be read by, or used to steer, candidate
generation or simulation.

| Label | Candidate bitstring | Reported overlap |
|---|---|---:|
| P6-A1 | `11100011000101111111011101011001110100110110000011010010010010` | 30/62 |
| P6-A2 | `11010000011001111100000010011000110100111101100000111100011010` | 32/62 |
| P6-A3 | `10011111010101011010100010111010001100010100101011101001110010` | 35/62 |
| P6-A4 | `11001011010111011010100010111011101100110100101111100001110110` | 33/62 |
| P6-A5 | `11011011110101011010100010111011001100010100000011100001110010` | 34/62 |
| P6-A6 | `10011011110101011010100010111010001100010100100011100001110010` | 35/62 |
| P6-A7 | `11011111110101011010100010111010001100010100101011101001110010` | 35/62 |
| P6-A8 | `10011111110101011010100010111010001100010100101011101001110010` | **36/62** |

P6-A8 is currently the strongest supplied reference at 36/62. When a new
candidate is produced, compare it against this set for provenance and
similarity, but obtain its actual overlap independently; similarity to a
reference string does not establish that it is the correct solution.

The previously unscored D128 seed-456 candidate was later evaluated externally
at **34/62**:
`11111100011101000101100111111010100101110111100100111101110101`.
It is therefore now an additional post-hoc constraint, not an unscored prior.

## 7.7 D128 seed confirmation and D512 screen

The D128/cutoff-0.005 sampling run with seed 123 completed all 2,593 gates and
produced a beam candidate identical to P6-A1 (30/62). A same-configuration
seed-456 run also completed, but its top candidates were 25--26 bits from the
closest scored references. The two runs therefore establish seed instability;
this configuration is retained as a diagnostic record and is not a solution
route.

The planned D512 cutoff-6e-4 screen was run and is reported in §7.8. It did not
produce a sample, so later work moved to structural reconstruction and fixed-
candidate feasibility rather than repeating the same MPO screen. The supplied
overlap table remains post-hoc evidence only.

## 7.8 D512 faithful screen result

The bounded D512 screen (`cutoff=6e-4`, `flip_freq=2`, four
`bond_profile` route candidates, seed 123) was stopped after reaching only
86/2593 work gates and then making no meaningful progress for roughly 27
unswap cycles. It reached peak bond 320 without the configured bond cap of 512
being binding, and no samples or candidate were produced because the run was
partial.

This is below the previous 138--150-gate ceiling, so the current MPO route is
stopped. The next work should be structural reconstruction or fixed-candidate
amplitude adjudication. The P6 reference overlaps remain available only for
post-hoc comparison.

## 7.9 Bounded structural reconstruction probe

The first answer-blind structural scan is recorded at
`results/p5_p6_p8_recovery/P6/structural/p6_structural_bounded.json`.
Ordered two-qubit interaction matching was weak: its best bounded result was a
32-edge window centered at interaction 1747, score 0.15625 versus shuffled-null
mean 0.08789 (z=1.49, empirical p=0.235 with 16 controls). This is not enough
to claim an ordered mirror.

Local-unitary matching produced a more useful reconstruction lead near layer
207, span 16, with the right patch conjugated: assignment score 0.75964,
support 1.7419, and z=15.55 against the scan's random-permutation baseline.
This identifies a patch/permutation hypothesis for a deeper structural pass; it
does not reconstruct the answer bitstring and its baseline is not equivalent to
the optimized ordered-match null, so it should not be treated as a solution
probability.

## 7.10 Fixed-candidate amplitude adjudication feasibility

`scripts/p6_fixed_amplitude_probe.py` now provides a fixed-candidate, oracle-
blind rehearsal/amplitude interface. Rehearsal was run over P6-A1--A8 and the
two D128 candidates at
`results/p5_p6_p8_recovery/P6/structural/p6_amplitude_rehearsal_refs.json`.
All candidates have the same contraction estimate for this circuit:
`C=49.3953` (approximately 10^49 floating-point work) and `W=119`. The
candidate bitstring changes the boundary tensor values but not this greedy
contraction topology. Exact amplitude adjudication is therefore not currently
practical on this 62-qubit, 10,486-operation representation; attempting it
would be another unbounded run rather than a bounded evaluation.

The fixed-candidate phase remains useful as a method, but it must be applied
after structural reduction (for example, a smaller reconstructed patch or a
candidate family with a tractable reduced circuit). Supplied 30/62--36/62
overlaps are not used by the probe and remain strictly post-hoc references.

## 7.11 Structural candidate-family reduction

The layer-207 lead was converted into a small, tagged hypothesis family at
`results/p5_p6_p8_recovery/P6/structural/p6_structural_candidate_family.json`.
The family contains 12 unique candidates generated from the two D128 outputs
(seed 123 and seed 456) under identity, the inferred local-unitary
permutation, its inverse, reversal, and complement transforms. Each candidate
retains provenance and the structural lead that generated it.

The patch itself does not reduce the full circuit: the 16-layer window still
touches 57 of 62 wires and 186 two-qubit events. Therefore it is not safe to
contract that window as though it were an isolated small circuit. The correct
next reduction is to use the inferred permutation as a constraint in a deeper
patch reconstruction, then adjudicate only candidates surviving that
constraint. The generated family is a bounded hypothesis set, not evidence of a
valid P6 answer.

## 7.12 Constrained reconstruction result

The inferred layer-207 permutation was tested as a prior over mirrored
two-qubit windows of width 16, 32, 64, 128, and 256 interactions. The fixed
mapping matched 0 edges in every window. Allowing at most ten local transposition
refinements recovered scores from 0.25 down to 0.043, while independently
optimized assignments scored 0.188, 0.25, 0.078, 0.086, and 0.078 respectively.
The corresponding fixed-mapping fingerprint scores over layer spans 16--96
were only 0.39--0.43, with row-wise best matches around 0.68--0.74.

This rejects the layer-207 permutation as a global reconstruction prior. It is
likely a local one-qubit-unitary coincidence or a correspondence that does not
preserve the two-qubit interaction stream. The bounded results are recorded at
`results/p5_p6_p8_recovery/P6/structural/p6_constrained_reconstruction.json`.
No amplitude adjudication was launched, and no new candidate is considered
validated. The next structural attempt should use a different invariant—such as
two-qubit patch fingerprints or graph/backbone constraints—before generating
another candidate family.

## 7.13 Exact small-patch motif and constrained family

The surrounding-neighborhood check did not support the motif as a global
correspondence. Under the proposed `(22,25,36) -> (21,58,6)` mapping, the
incident-edge count differences were 7, 12, 19, and 29 for radii 16, 32, 64,
and 128 interactions respectively; the mapped right wires were nearly isolated
where the left wires had substantial local degree. The six patch hypotheses are
therefore retained for audit but rejected for amplitude adjudication. This
closes this particular patch lead without claiming a P6 solution.

The bounded 3-qubit patch scan found an exact-sized local motif worth retaining:
the left patch beginning at event 1636 on wires `(22,25,36)` matches the
right patch beginning at event 1861 on wires `(6,21,58)` with the right patch
ordered `(21,58,6)` and adjointed. Its phase-insensitive local-unitary fidelity
is 0.997799. The adjacent 3-entangler extraction gives the same result; the
match is not caused by padding a larger unrelated window.

Using that correspondence as a local, rather than global, constraint produced
six tagged hypotheses from the two D128 seed outputs (identity, patch-cycle,
and inverse-cycle transforms) at
`results/p5_p6_p8_recovery/P6/structural/p6_patch_candidate_family.json`.
The scan and match ledger are at
`results/p5_p6_p8_recovery/P6/structural/p6_patch_fingerprint_scan.json`.
These are the first structurally motivated candidates from the new route, but
they remain unvalidated: the local motif alone does not determine the global
answer bits. The larger-neighborhood check in §7.13 did not support the motif as
a global correspondence, so this candidate family is closed as a recovery route.

## 7.14 2026-08-31 reassessment

The answer-blind permutation-MPS run with the saved annealed ordering completed
all 10,486 parsed operations at D128/cutoff `1e-12`, but retained only
`1.6733e-20` against the calibrated P6 gate `100*2^-62 = 2.168e-17`. Its
near-flat top-1/top-2 ratio (`1.020x`) classifies the output as a truncation
artifact. The result is recorded at
`results/new_p6_p8_20260831/p6_perm_annealed_D128.json`.

The completed loose-cutoff D128 extraction was independently audited over 10,000
samples. Every sample was unique, yet the majority reproduced P6-A1 exactly;
the split-half majority differed by one bit and 61/62 bootstrap bits were
stable. This is a reproducible truncation bias, not a recovered answer. The
audit is at
`results/new_p6_p8_20260831/p6_d128_extract_analysis/analysis.json`.

The latest overnight stages add no candidate: D512/cutoff `1e-3` reached
180/2593 before the no-progress guard, while pair-lookahead stages reached only
24/2593 before wall/user stops. The current next step is a proper
`1.5e-3`--`1.875e-3` bisection and, only if it passes calibration, an adaptive
cutoff-rescue controller. Do not describe P6 as solved or as mathematically
impossible.


---

# 8. What P8's solution implies for P6 (2026-09-01)

P8 was solved by **materializing the MPS at its routing stall** rather than
escaping it. Its compression aborted at 804/808 with 4 work gates left inside 2
left and 17 right leftover layers; `mpo_to_mps` folds those residual layers in
before applying the compressed core, and the resulting state sampled the correct
answer (peak 0.038, top1/top2 6.44x).

**This does not transfer to P6, and the reason is quantitative.** The promotion
criterion is not "did the run consume all work gates" but "is the residual small
enough to materialize faithfully":

| circuit | stall | work gates remaining | materializable? |
|---|---|---:|---|
| P8 | 804/808 | **4** | yes -- solved this way |
| P6 (6e-4, best) | 148/2593 | **2445** | no |
| P6 (1.75e-3) | 164/2593 | **2429** | no |

No materialization can absorb ~2400 remaining gates; that is the whole circuit.
P6's problem was never the last few gates -- it is that the router stalls at
5-7% of the circuit at any cutoff tight enough to preserve fidelity, and that
the one cutoff which does complete (2e-3) destroys the peak.

So P6's status is unchanged: **`NONCONVERGED`**, with the open experiments in
§7.5 still the right ones. The P8 result does, however, sharpen what "close
enough" means for an MPO stall, and it is worth re-checking any future P6 run
against the residual-size criterion rather than the completion criterion.


---

# 9. Readout hypothesis tested and refuted (2026-09-01)

## Motivation

Both completed P6 runs at cutoff 2e-3 called `mpo_to_mps` with
`cutoff=args.cutoff` and no explicit `max_bond`, so the **final MPO->MPS
materialization ran at cutoff 2e-3** -- the loosest in the campaign -- while the
bond cap was the function default 4096, never 512. The compressed MPO ended at
bond 27-40 holding 43-46k elements, yet the materialized MPS collapsed to bond
4-11 and a few hundred elements.

That raised a specific, cheap hypothesis: **the peak survived compression and
was destroyed at readout.** If true, P6 would be recoverable without touching
the compression at all -- the same class of oversight (an unset default) that
had hidden P8's solution.

## Experiment

Identical compression, single changed variable. `--materialize-max-bond 4096
--materialize-cutoff 1e-8` against the previous effective `4096 / 2e-3`. To keep
the compression byte-identical, the two flags were added to the local
`p6-flipfreq` worktree (defaults preserving prior behaviour) rather than using
`7296a2a`, whose `flip_freq` code path differs.

Compression reproduced exactly: `end compressing (left: 2, right: 2)`,
final MPO bond **27**, **43,456** elements -- identical to `p6main_c2e3_long`.

## Result: negative

| run | materialize cutoff | MPS bond | MPS elems | peak frac | top1/top2 |
|---|---|---:|---:|---:|---:|
| `p6_d512_cut2e3` | 2e-3 | 4 | 294 | 0.001 | 1.02x |
| `p6main_c2e3_long` | 2e-3 | 11 | 2290 | 0.001 | 1.06x |
| **high precision** | **1e-8** | **18** | **8842** | **0.001** | **1.058x** |

Decoder top-1 `1.21e-08`; 1000/1000 samples unique.

Removing the truncation almost entirely retained 4x more state and produced an
**identically flat** distribution. The 1.06x -> 1.058x change is noise.

**The peak was destroyed during compression at 2e-3, not at readout.**

A second observation reinforces this: with bond 4096 available and cutoff 1e-8,
the state materialized to bond **18**. It is not being crushed by truncation --
the MPO at bond 27 simply does not contain more structure than that.

## Consequences

Now excluded for P6: cutoff window at 2e-3, depth, materialized-state size as a
fidelity diagnostic, route/trajectory quality, **and readout precision**. The P8
tail-materialization mechanism is also excluded, for the residual-size reason in
section 8.

The open experiments in section 7.5 are unchanged, but the priority ordering
should now be read pessimistically for the tensor route: every cutoff tight
enough to preserve information stalls the router at 5-7% of the circuit, and the
one cutoff that completes has already discarded the answer. A usable window
would have to be very narrow.

Artifact:
`results/p5_p6_p8_recovery/P6/mpo/cut2e3_high_precision_materialize/`.


---

# 10. PyZX exact reduction closed (2026-09-01)

Measured in `results/p6_pyzx_structural_metrics_20260901.json`. Both exact ZX
reductions were run on P6. **Both make it worse on every metric that matters:**

| metric | original | `full_reduce` | `teleport_reduce` |
|---|---:|---:|---:|
| two-qubit ops | **3,494** | 3,631 | 3,494 |
| one-qubit ops | **6,992** | 22,442 | 94,786 |
| total ops | **10,486** | 26,073 | 98,280 |
| depth | **416** | 1,119 | 3,611 |
| interaction edges | **658** | 710 | 658 |
| natural cutwidth | **329** | 380 | 329 |

`full_reduce` *increases* the two-qubit count, the edge count, the cutwidth and
the depth. `teleport_reduce` preserves the interaction structure exactly -- as
designed, it keeps the graph fixed -- but at 94,786 single-qubit gates, a 13.6x
blow-up.

The motivating precedent does not transfer: PyZX cut P9's two-qubit count by 51%
(3,834 -> 1,878). P9's structure is compressible under ZX rewriting; P6's is not.

This is consistent with everything else measured. **P6 is not a circuit with
hidden redundancy waiting to be simplified.** Its 2,593 work gates carry genuine
content, which is why truncation error accumulates across them (section 9) and
why the CAMPS diagnostic found no small non-Clifford residual to isolate
(`P6_CAMPS_FEASIBILITY.md`).

## Routes closed for P6, with the evidence

| route | closed by |
|---|---|
| bond dimension | `selected_absorbs_hit_max_bond = 0` on every D=512 run |
| element threshold | 0 of 1170/259/482 absorb rows had both probes over threshold |
| cutoff window | P5/P9 preserve their answers at 1.5e-3 and 2e-3 |
| depth | P9 exact at 2e-3 with 1885 gates |
| route/trajectory quality | `flip_freq=2` vs default: equally flat |
| readout precision | cutoff 1e-8: identically flat, state materializes to bond 18 |
| P8 tail materialization | needs a small residual; P6 leaves ~2,400 gates |
| dense-connectivity story | P6 is 34.8% dense vs P5 61.1% and P9 69.4%, both solved |
| structural (layer-207) | fixed mapping matched 0 edges at widths 16-256 |
| **CAMPS** | all four circuits saturate `nu = min(left,right)` |
| **PyZX** | both reductions increase cost |

Remaining: split absorb/route cutoffs with rescue pulses (section 7.5), and the
1.875e-3 scalar endpoint. Both are due diligence rather than promising leads.


---

# 11. Split absorb/route cutoffs closed by the P5 control (2026-09-01)

## The idea

The solver used a **single cutoff for two different operations**: absorbing
physical circuit layers (real circuit evolution) and compressing during
unswapping (reordering the MPO). Coupling them forces P6's central trade -- a
tight cutoff preserves the peak but stalls the router, a loose one lets routing
finish but destroys the peak.

`--route-cutoff` (solver commit `ff86d96`) threads a separate cutoff into the
`unswap()` call only, leaving the three absorb-side compressions on `--cutoff`.
Defaults to `None -> cutoff`, so prior behaviour is unchanged.

## Control: P5 must still return 44/44

Run before touching P6, with `c_absorb = 6e-4` (validated) and
`c_route = 2e-3` (loose routing).

| | single cutoff 6e-4 | split: absorb 6e-4 / route 2e-3 |
|---|---:|---:|
| overlap | **44/44** | **43/44** |
| peak fraction | 0.012 | 0.002 |
| decoder top-1 | 1.09e-2 | 2.76e-3 |
| top1/top2 | 7.8x | 3.10x |

```
truth      11110000001110100101110011111101010001100001
split-cut  11110000001110100101110011111101010101100001
                                             ^ one bit wrong
```

**Control FAILED.** The split was not run on P6: a controller that damages a
known answer cannot be trusted to produce an unknown one.

## What it establishes

The premise -- that routing truncation is nearly free because unswapping only
reorders the MPO -- is **wrong**, and worth recording so it is not re-proposed.
Loosening truncation during unswapping degraded P5 by roughly the factor that
loosening it during absorption would have (peak 0.012 -> 0.002, comparable to
what a global 2e-3 does to P5).

The reason: unswapping does not permute indices. It applies SWAP layers as
tensors and recompresses, so **every unswap step is a lossy operation on the
state**. "Just reordering" was the error in the idea.


---

# 12. The scalar-cutoff question, closed empirically (2026-09-01)

Section 7 correctly noted that the sub-2e-3 interval had never been probed to a
genuine endpoint: both earlier runs were stopped by scheduling decisions rather
than by the solver. That gap is now closed by direct measurement on P6.

Run `p6_c1p875e3_endpoint`: cutoff **1.875e-3**, `flip_freq=2`, D512, guard 150
(generous but finite, so a real stall terminates cleanly), 12 h budget.

**It completed** -- 2593/2593, `termination_reason: completed`, leftover L2/R2,
9278 s. That is itself new: 1.875e-3 was expected to stall like 1.75e-3 (164) and
1e-3 (180), so the completion boundary lies *below* 1.875e-3 rather than between
it and 2e-3.

**And the peak is absent:**

| | peak fraction | decoder top-1 | top1/top2 |
|---|---:|---:|---:|
| bar from three verified answers | >= ~0.012 | >= ~1e-3 | >= ~3x |
| P6 @ 1.875e-3 | 0.001 | 2.01e-07 | **1.010x** |
| P6 @ 2e-3 | 0.001 | 2.8e-07 | 1.06x |

1000/1000 samples unique. The candidate also violates **12 of 13** recorded
overlaps (`scripts/p6_verify_candidate.py`), so it is provably not the answer.

## The scalar cutoff sequence, complete

```
6e-4       stalls    86-148 / 2593
1e-3       stalls   180 / 2593
1.75e-3    stalls   164 / 2593
1.875e-3   COMPLETES 2593 / 2593  ->  flat (1.010x)
2e-3       COMPLETES 2593 / 2593  ->  flat (1.06x)
```

Every cutoff that completes destroys the peak; every cutoff that preserves
information stalls the router. **There is no window** -- established on P6 at the
boundary itself, not inferred from P5/P9 behaviour. This was the last legitimate
gap in the argument of section 7 and it is now measured.
