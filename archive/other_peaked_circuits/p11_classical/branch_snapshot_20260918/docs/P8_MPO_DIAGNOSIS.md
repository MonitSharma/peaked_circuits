# P8 MPO diagnosis — no verified peak; controller endpoint remains incomplete

> **STATUS UPDATE 2026-08-31.** Sections 1--5 below are the historical
> nineteen-run baseline. The later controller campaign reached 804/808, but
> both 804 results came from the earlier dirty `e1a6eef` solver checkout and
> still stopped before sampling. Clean `7296a2a` tail attempts under the safe
> conda runtime reached 781/808 and 782/808 before intentional stops. A new
> D256 permutation-MPS run and structural scans also failed their diagnostic
> gates. There is no verified P8 candidate.

**Circuit:** `P8_grid_888_iswap.qasm` — 40 qubits, depth 129, 888 iSWAP + 1,816 U3,
consolidating to **808 work gates**. 63 interaction edges, max degree 4,
grid-like (5x8-ish) geometry. SHA256
`ba42c338478fdfbc0241ec2289b3159bfde5dffc71603ac588ec0755fba1a484`.

**Solver:** midpoint MPO + greedy unswapping + SABRE routing (`p9solver`,
commit `b1bed0a`) via `scripts/run_p11_mpo.py`.
**Environment:** conda `p9-openblas` (Python 3.10.21, SciPy 1.15.2).
`.venv-p9-isolated` (3.10.16 / SciPy 1.15.3) **segfaults** at D=512.

No target answer or portal score was read during candidate generation.

---

## 0. Calibration

| control | peak fraction | decoder top-1 | outcome |
|---|---|---|---|
| P9 (5 runs, D=512, cutoff 6e-4) | 0.036–0.096 | 5.3e-2 | correct |
| **P5** (D=512, cutoff 6e-4, bond_profile, guard relaxed) | **0.012** | **1.09e-2** | **correct 44/44** |
| P9 loose control (cutoff 5e-3) | 0.001 | 4.9e-9 | wrong |

P5 sets the bar: a **1.2% peak is sufficient**. So if P8 ever completed, its top
sampled string would very likely be the answer. **P8 never reached sampling.**

---

## 1. Historical baseline: nineteen runs, sixteen configurations

| tag | route | sel-mode | absorb | ctr | seed | guard | gates | term |
|---|---|---|---|---|---|---|---|---|
| `d512_c6e4` | 1/none | bond | elems | .5 | 123 | 2 | 785 | no_progress |
| `d512_c6e4_noguard` | 1/none | bond | elems | .5 | 123 | −1 | 785 | limit cycle (killed) |
| `d512_bondprofile` | 4/bond_profile | bond | elems | .5 | 123 | 15 | 794 | no_progress |
| `d512_routeproxy` | 4/bond_profile | bond_route_proxy | elems | .5 | 123 | 15 | 781 | no_progress |
| `d512_center058` | 4/bond_profile | bond | elems | **.58** | 123 | 15 | **90** | no_progress |
| `d512_patience60` | 4/bond_profile | bond | elems | .5 | 123 | 60 | 797 | no_progress |
| `d512_bp_nolimit` | 4/bond_profile | bond | elems | .5 | 123 | −1 | 797 | wall limit |
| `d512_bp_seed777` | 4/bond_profile | bond | elems | .5 | 777 | 60 | 791 | no_progress |
| `d512_bp_seed456` | 4/bond_profile | bond | elems | .5 | 456 | 60 | 787 | no_progress |
| `d512_bp_seed2024` | 4/bond_profile | bond | elems | .5 | 2024 | 60 | **799** | no_progress |
| `d512_bp_absorb_bond_l2` | 4/bond_profile | bond | **bond_l2** | .5 | 123 | 60 | 780 | no_progress |
| `d512_bp_absorb_max_bond` | 4/bond_profile | bond | **max_bond** | .5 | 123 | 60 | 797 | wall limit |
| `nonbond_augment_s2024` | 4/bond_profile | proxy+**augment** | elems | .5 | 2024 | 60 | **58** | exploded (bond 512) |
| `nonbond_hybrid_s123` | 4/bond_profile | proxy+**hybrid** | elems | .5 | 123 | 60 | 786 | no_progress |
| `sel_bond_aligned` | 4/bond_profile | **bond_aligned** | elems | .5 | 2024 | 60 | 779 | no_progress |
| `sel_layer` | 4/bond_profile | **layer** | elems | .5 | 2024 | 60 | **63** | blowup |
| `sel_pair_lookahead` | 4/bond_profile | **pair_lookahead** | elems | .5 | 2024 | 60 | 742 | wall limit (1 h — too short) |
| `pairlook_long` | 4/bond_profile | pair_lookahead | elems | .5 | 2024 | 60 | **792** | flat-lined, killed at 3h35m |
| `d1024_c1e4` | 1/none | bond | elems | .5 | 123 | 20 | 774 | keyboard_interrupt |

**The original baseline runs land in a 20-gate band: 779–799 of 808
(96.4–98.9%).** None reached `[end compressing]` or sampling. Later controller
results are recorded separately in §6; **no P8 candidate exists.**

---

## 2. What is ruled out

### 2.1 Not entanglement-limited — the decisive evidence

`selected_absorbs_hit_max_bond = 0` on **all nineteen runs**. The bond cap never
once constrained an absorption.

More telling: **final bond at the stall ranges 64–176 while the stall point
barely moves.** The run ending at bond 64 (`seed777`, 791 gates) and the one at
bond 176 (`bond_aligned`, 779 gates) stall within 12 gates of each other. A
2.75x spread in bond produces no meaningful change in outcome. If entanglement
were the constraint this could not happen.

Raising D=512 -> 1024 changed nothing (774 gates, and bond only reached 318).

### 2.2 Not element-threshold-limited

Across the three deepest runs, **0 of 1170 / 259 / 482 absorb rows had *both*
probes over `unswap_threshold`.** A legal absorb was always available. The
threshold shapes *which* absorb is chosen (selected sizes pin just under 500k)
but never blocked progress. Raising it is not the fix.

### 2.3 No cutoff rescue shown in the baseline

The termination message classifies some stalls as `entanglement_blowup` and
recommends changing `--cutoff`. **That classification is misleading**: it fires
whenever `elems >= 0.5 * unswap_threshold` (`pipeline.py:2118`), a soft
heuristic, not a measurement of what blocked. Per-row telemetry shows nothing
blocked. Cutoff was not varied in this baseline because 6e-4 is the P9/P5-
validated value. The later tail attempts also kept 6e-4, so these experiments
do not prove that a different P8 cutoff cannot help.

---

## 3. The actual mechanism

Every stalled run ends in the **same geometry**:

```
t_u_l: 404/404      left half fully drained
t_u_r: 380-390/404  right half stranded
leftover  left: 2   right: 24-54
```

Left exhaustion is an endpoint correlate, **not the cause**. Across the three
deepest runs the halves advance nearly in lockstep: peak skew is only 20--29
gates out of 404, and the left reaches 404 only at 97--98% total progress,
essentially simultaneously with the stall. The terminal skew is 9 gates for
seed 2024, 11 for patience 60, and 16 for pair lookahead. Balance-oriented
absorb scores and the shifted centre were therefore aimed at a non-causal
asymmetry, consistent with their failure.

The causal measurement is instead that the router inserts SWAP layers, the
absorber consumes them (**zero work gates**), and the unswapper removes exactly
those swaps without making a specific remaining consolidated gate absorbable.

Measured directly in `d512_c6e4_noguard` (guard disabled): a clean **period-1
attractor** — 35 unswap cycles at 785/808, post-unswap state cycling among five
near-identical configurations (266,824 / 267,032 / 267,240 / 267,448 / 267,656
elements, all at bond 103, a 0.3% spread). The guard at its default of 2 was
detecting a *real* deadlock, not terminating prematurely.

Fraction of absorb steps consuming zero work gates: **P5 49%, P6 74%, P8 24%.**

This is exactly `docs/P11_ROUTING_DIAGNOSIS.md` §1: *"routed layers oscillate
rather than drain — the greedy keeps applying bond-neutral swaps that never
unblock the next work gate."*

---

## 4. Every shipped remedy tested

| lever | result |
|---|---|
| guard 2 -> 15 -> 60 -> unlimited | 785 -> 794 -> 797 -> 797. Asymptotic. |
| `route_score bond_profile`, 4 candidates | +9 gates over plain. Best baseline. |
| `bond_route_proxy` (veto, default) | 781 — worse |
| `bond_route_proxy` + allow-nonbond **hybrid** | 786 — no better |
| `bond_route_proxy` + allow-nonbond **augment** | **58** — bond hit 512 at gate 58; reproduces the P11 §6a explosion |
| `unswap_select_mode bond_aligned` | 779 — worse |
| `unswap_select_mode layer` | **63** — blowup, both halves stranded |
| `unswap_select_mode pair_lookahead` | 792 — best of the non-greedy selectors; never tripped the guard; flat-lined (0 gates in 30 min at cycle 61) |
| `absorb_score max_bond` / `bond_l2` | 797 / 780 — no better |
| `center_ratio 0.58` | **90** — far worse |
| seeds 123 / 456 / 777 / 2024 | 794 / 787 / 791 / 799 — **10-gate spread, zero successes** |

**The seed result matters.** On P5, seed 123 completed 902/902 while seed 777
stalled at 875 — a 27-gate spread with one clean success. On P8, four seeds
cluster in 10 gates with none through. P8's barrier is **structural, not route
luck.**

`pair_lookahead` deserves a note: it was the only selector that kept both halves
balanced for most of its run and used ~10x fewer unswap cycles per gate (12
cycles for 749 gates vs 20–60 for greedy). It was first killed by a 1-hour wall
limit that was too short — an operator error, not an algorithm failure — and
rerun with 12 h. It still converged to `left: 404/404` and flat-lined at 792.

---

## 5. Conclusion

**`CURRENT_METHODS_EXHAUSTED`** for the historical `p9solver` MPO baseline on
P8; the overall P8 problem remains unresolved because the late-controller tail
has not been sampled.

- The nineteen-run baseline spans the shipped routing scores, unswap selectors,
  absorb scores, centre ratios, seeds and patience levels and ends at
  **779–799 / 808** without sampling.
- The later absorption-schedule controller reached 804/808 but also did not
  sample. The evidence supports an incomplete controller endpoint, not a proof
  that no other scheduler can finish.

This independently reproduces the routing-attractor pattern seen in
`P11_ROUTING_DIAGNOSIS.md` §6a. A live late-gate controller was subsequently
integrated in the external P8 worktree and is evaluated in §6; it changes the
endpoint but has not yet yielded a sampled candidate.

**The difference from P11 is worth stating: P11 fails at ~3% of its circuit;
P8 fails at 98.9%.** Nine gates stand between the best run and what P5's
calibration says would very likely be the answer. That makes integrating the
beam controller — or any scheduler that proves a remaining work gate
absorbable — a far higher-value target on P8 than on P11.

**Do not** spend further effort on blind repetitions of the historical baseline:
larger D, larger `unswap_threshold`, more seeds, more patience, or additional
shipped routing policies. The only currently justified MPO experiment is to
reproduce the 804 endpoint in a clean environment and materialize its final
tail.

---

## 6. Late gate-unlock beam implementation (2026-08-30)

The projected-distance prototype in `compiler/beam_controller.py` remains a
diagnostic only. A new opt-in controller has instead been implemented directly
against the production compressor in the isolated solver worktree:

```
<local-user>/code_projects/qat/peaked-mpo-solver-p8-beam
branch: codex/p8-gate-unlock-beam
```

The original solver checkout used by the active P6 campaign is unchanged.

The new controller is **live and joint** rather than a static identity-order
projection. At each post-unswap rewire after the late-stage trigger it:

1. generates multiple deterministic SABRE suffix routes for both halves;
2. carries actual live MPO states through a finite-horizon search;
3. rejects every transition whose resulting MPO violates the exact absorption
   element or bond budget;
4. searches joint `(left route, right route, absorb-side sequence, MPO)` states,
   while also supporting the one-sided terminal state directly;
5. ranks first by the number of consolidated work gates proven absorbable,
   then by swap-only motion, SWAP count, and live MPO cost;
6. uses left/right balance only as a late tie-breaker;
7. returns a preferred absorb-side sequence, with the exact MPO absorbability
   checks retaining final authority and falling back safely if a projection is
   illegal.

It is disabled by default. The new controls are:

```
--late-gate-beam
--late-gate-beam-remaining 40
--late-gate-beam-width 16
--late-gate-beam-depth 24
--late-gate-beam-no-progress-trigger 1
```

The controller activates only in the last 40 work gates and, by default, after
one prior zero-work cycle. It can search both halves jointly or search the
remaining side after the other half has exhausted. It therefore tests the
measured gate-unlock hypothesis directly rather than assuming that left-side
exhaustion caused the attractor.

Validation completed before a full P8 launch:

- six deterministic controller unit tests pass, including a case where the
  shorter projected route is rejected because its target gate violates the
  live MPO budget and a longer route unlocks the gate;
- the existing decoder tests pass in the `p9-openblas` numerical environment;
- a four-qubit end-to-end MPO smoke run exercised two live gate-beam rewires,
  including the one-sided controller path;
- the same smoke configuration with the feature disabled emitted zero
  gate-beam rows, confirming that the default path is unchanged;
- Python compilation and `git diff --check` pass.

At the time of this 2026-08-30 implementation note, a full P8 run was
deliberately not launched while the isolated P6 campaign was active. The
subsequent clean-runtime tail attempts are recorded in §6.6. The first P8
experiment should retain the best P8 fidelity settings
(`D=512`, cutoff `6e-4`, seed 2024, four route candidates, `bond_profile`) and
add only the late gate-unlock controller. This makes the comparison against
the 799/808 baseline interpretable.


---

# 6. 2026-08-30 update — controller campaign (results reported by the P8 worktree)

Work done in `peaked-mpo-solver-p8-beam` (branch `codex/p8-gate-unlock-beam`).
Results below are **as reported by that campaign**, not re-measured here.
The 804/808 rows came from the earlier `e1a6eef` dirty worktree; they are not
clean-branch reproductions. The clean `7296a2a` follow-up is reported in §6.6.
Fixed throughout: D=512, cutoff 6e-4, `unswap_threshold` 5e5, seed 2024,
`--route-candidates 4 --route-score bond_profile`.

## 6.1 Results

| intervention | gates | terminal split |
|---|---|---|
| plain greedy (baseline, seed 2024) | 799/808 | L=404/404 R=395/404 |
| `flip_freq=1` | 802/808 | — |
| **`flip_freq=2`** | **804/808** | — (best) |
| `flip_freq=4` | 802/808 | — |
| balanced `delta=0.05` | 792/808 | — |
| balanced `delta=0.02` | 799/808 | **L=404/404 R=395/404** |
| cycle-detect + 1-cycle tabu | 793/808 | L=404/404 R=389/404 |
| tail beam width 4 / horizon 2 | 794/808 | — |
| tail beam width 8 / horizon 4 | 799/808 | **L=404/404 R=395/404** |
| phase schedule 2->1 | 804/808 | no-progress cycle limit |
| phase schedule 2->4 | 804/808 | no-progress cycle limit |

No configuration has completed 808/808. **No P8 candidate exists.**

## 6.2 The decisive observation: three policies, one terminal state

```
plain greedy (seed2024)   799/808   L=404/404  R=395/404
balanced delta=0.02       799/808   L=404/404  R=395/404
tail beam w8/h4           799/808   L=404/404  R=395/404
```

Local greedy scoring, balance-constrained scheduling, and **depth-4 lookahead
search** converge on the bit-identical terminal state in the historical baseline.
The later absorption schedules reach a different 804/808 endpoint, so the
stronger claim that no policy over the action space can escape is not supported.
What remains established is that none of the tested policies reaches sampling.

Cycle telemetry confirms genuine recurrence: 94 routing-state hashes recorded,
**only 32 unique** (62 repeats). The states are genuinely revisited; filtering
individual swaps (tabu) did not change the reachable set, and cost 6 gates.

## 6.3 The one dimension with demonstrated leverage

Every intervention that modified **swap selection** landed on 799
(tabu 793, beam-h2 794, beam-h4 799, route-proxy 781, bond_aligned 779).
Every intervention that modified the **absorption schedule** reached a
*different* terminal state:

```
no flip        799
2->1 schedule  804
flip_freq=2    804
2->4 schedule  804
```

`--flip-freq` was previously unreachable: `pipeline.py` supports it (lines 1703,
1775) but `cli.py:829` hard-coded `flip_freq=None`. Exposing it produced the
best P8 result on record.

The tested absorption schedules explain the improvement from 799 to 804, but
none completed. Further schedule sweeps are lower value than replaying the
804 trajectory and materializing its final four gates.

## 6.4 Status

Current status: **no verified P8 candidate**. The best historical endpoint is
804/808 (99.5%), still short of sampling. The provenance-sensitive next step is
the clean replay/tail experiment described below.

## 6.5 Post-hoc P8 bitstring reference set

The following six 40-bit strings were supplied for post-hoc evaluation, with
the reported overlaps shown below. They are comparison anchors for future
candidate analysis, not inputs to candidate generation or simulation.

| Label | Candidate bitstring | Reported overlap |
|---|---|---:|
| P8-A1 | `0101010001111100110101000111001001001000` | 19/40 |
| P8-A2 | `0110000010001100011101101000101101111011` | **23/40** |
| P8-A3 | `1001100010111101101101110011111010010011` | 19/40 |
| P8-A4 | `1001100010111101111101101011111010010011` | 18/40 |
| P8-A5 | `0110100010111101110010011101101100011011` | 18/40 |
| P8-A6 | `0010111110100001101010111000001111111011` | **24/40** |

P8-A6 is the strongest supplied reference at 24/40, followed by P8-A2 at
23/40. The strings are useful for measuring whether a new candidate belongs to
one of the existing approximate basins. Across these six references, several
positions show strong consensus (for example positions 7--11, 13--15, 17,
31, 36, and 38--40), which can help identify stable bits. However, this is not
a proof of correctness: the candidates are from approximate methods and their
disagreements show that the unstable positions remain unresolved. Any new
candidate still requires an independent overlap evaluation.

## 6.6 2026-08-31 clean-runtime follow-up

The new D256 annealed permutation-MPS run completed 2,704 parsed operations at
cutoff `1e-14`, but retained only `7.3925e-19` against the calibrated P8 gate
`100*2^-40 = 9.095e-11`. Its top-1/top-2 ratio was `1.020x` with a top-32
Hamming spread of `7.9`, so it is a truncation artifact, not a candidate. The
result is recorded at
`results/new_p6_p8_20260831/p8_perm_annealed_D256.json`.

The new unitary and graph/mirror scans found strong local optimized matches but
no stable global permutation: the graph scan's neighboring-window permutation
stability was `0.0167`. Their summaries are at
`results/new_p8_structure_20260831/unitary/summary.json` and
`results/new_p8_structure_20260831/hqap/summary.json`.

The tail-materialization implementation was exercised under conda
`p9-openblas` using the clean `7296a2a` controller. The `flip_freq=2` run stopped
at 781/808 and the 2->1 schedule stopped at 782/808, both by intentional
keyboard interrupt before the eight-gate eligibility threshold. No sample was
produced and no spontaneous crash occurred. The older 804/808 manifests belong
to the dirty `e1a6eef` checkout, and there is no checkpoint/resume artifact.

Consequently, P8 remains unresolved. The next justified run is a clean replay
of the exact controller configuration that reached 804/808, followed
immediately by tail materialization; another generic MPO parameter sweep is
not justified.


---

# 7. Why the exhaustion verdict was wrong (2026-09-01)

Everything measured in sections 1-5 holds: the attractor is real, it is
routing-limited rather than entanglement-limited, and no policy over the shipped
action space escapes it. Three qualitatively different controllers converge on a
bit-identical terminal state.

The error was treating "cannot consume all 808 work gates" as equivalent to
"cannot produce the answer". It is not. `mpo_to_mps` applies the residual layers
before the compressed core, so a run that stalls with **few enough gates
remaining** can still be materialized into a faithful full-circuit state.

At the 804 stall only 4 work gates remained, inside 2 left and 17 right leftover
layers. Folding those in at `materialize_max_bond=512` produced a state whose
sampled mode is the correct P8 answer, at peak fraction 0.038 and top1/top2
6.44x.

**The generalisable lesson:** the promotion criterion for an MPO run should not
be "did it consume all work gates" but "is the residual small enough to
materialize faithfully". A stall at 804/808 is a solved circuit; a stall at
150/2593 (P6) is not, because no materialization can absorb 2443 remaining
gates. That distinction is what separates P8 from P6, and it was not drawn in
any earlier revision of this document.
