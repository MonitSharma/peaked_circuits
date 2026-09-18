# Cutoff/fidelity calibration for the MPO route

Measured 2026-08-30 against **known answers** (P5 and P9), to separate two
questions that had been entangled in every prior P6/P8 experiment:

- **completion** — can the solver consume all work gates?
- **fidelity** — does the peak survive the truncation used to get there?

All runs: D=512, `unswap_threshold` 5e5, seed 123, conda `p9-openblas`
(Python 3.10.21 / SciPy 1.15.2). P5/P6 additionally use
`--route-candidates 4 --route-score bond_profile`.

> **2026-08-31 update.** The later P6 D128 permutation-MPS and P8 D256
> permutation-MPS diagnostics both failed their fidelity gates. Clean P8 tail
> attempts stopped before sampling. These results do not change the calibration
> threshold below, but they reinforce that large approximate-state ratios are
> not sufficient evidence of a peak.

---

## 1. The measurements

| circuit | qubits | work gates | cutoff | overlap | peak frac | decoder top-1 | top1/top2 |
|---|---|---|---|---|---|---|---|
| P9 | 56 | 1885 | 6e-4 | **56/56** | 0.048 | 5.3e-2 | 5.3x |
| P9 | 56 | 1885 | **1.5e-3** | **56/56** | **0.098** | 9.98e-2 | **23.1x** |
| P9 | 56 | 1885 | **2e-3** | **56/56** | 0.086 | 7.18e-2 | 4.5x |
| P9 | 56 | 1885 | 5e-3 | wrong (25/56) | 0.001 | 4.9e-9 | ~1x |
| P5 | 44 | 902 | 6e-4 | **44/44** | 0.012 | 1.09e-2 | 7.8x |
| P5 | 44 | 902 | **1.5e-3** | **44/44** | 0.012 | 1.16e-2 | 6.3x |
| P5 | 44 | 902 | 2e-3 | 42/44 | 0.004 | 3.39e-3 | 3.4x |
| **P8** | **40** | **808** | 6e-4 (tail-materialized at 804) | **40/40** | **0.038** | **2.86e-02** | **6.44x** |
| **P6** | **62** | **2593** | **2e-3** (default router) | — | **0.001** | **2.8e-07** | **1.02x** |
| **P6** | **62** | **2593** | **2e-3** (`flip_freq=2`) | — | **0.001** | **1.22e-08** | **1.06x** |

## 2. What this establishes

### 2.1 A looser cutoff is not inherently destructive — it can *improve* the peak

P9 recovers its answer at 6e-4, 1.5e-3 **and** 2e-3. Its best mode of the whole
campaign is at **1.5e-3** (peak 0.098, top1/top2 = 23x), better than at the
originally calibrated 6e-4. Treating 6e-4 as "the faithful cutoff" and anything
looser as suspect was wrong.

### 2.2 Depth is not the mechanism

P9 is 1885 work gates — 2.1x P5's 902, and 73% of P6's 2593 — and is exact at
both 1.5e-3 and 2e-3. An earlier hypothesis that P6's collapse was truncation
error accumulating over 2593 gates is **refuted**.

### 2.3 The materialized-state size is NOT a fidelity indicator

Proposed and then discarded the same day:

```
P9 @ 2e-3  -> correct 56/56, materialized bond 3,  total_elems 174
P5 @ 1.5e-3-> correct 44/44, materialized bond 20, total_elems 5108
P5 @ 6e-4  -> correct 44/44, materialized bond 50, total_elems 29856
P6 @ 2e-3  -> destroyed,     materialized bond 4,  total_elems 294
```

A correct answer came out of a 174-element state, smaller than P6's destroyed
294. **Judge on `top1/top2` and peak fraction only.**

### 2.4 Route quality does not rescue fidelity

Controlled single-variable test on P6 at the same cutoff (2e-3), same seed, only
the absorption schedule changed:

| router | gates | peak frac | top-1 | top1/top2 |
|---|---|---|---|---|
| default `bond` | 2593 | 0.001 | 2.8e-07 | 1.02x |
| `flip_freq=2` | 2593 | 0.001 | 1.22e-08 | 1.06x |

The `flip_freq=2` run was far healthier — balanced halves (L 449/1296,
R 462/1297 at mid-run), zero aborts across 175 cycles, peak bond 510, and it
reached 6x further than any previous P6 attempt before completing. It produced
an **equally flat** result, with a top-1 probability an order of magnitude
*worse*. Trajectory quality is not what destroys P6's peak.

## 3. Promotion threshold (three verified circuits)

Confirmed correct answers now span **P5 (44/44), P8 (40/40), and P9 (56/56)**,
at peak fractions 0.012, 0.038 and 0.048-0.098 respectively. P5 at 0.012 is the
binding case: a 3% peak gate would have discarded a correct answer. The usable
bar is a *distinct* mode, not a large one:

```
ACCEPT   decoder top-1 >= ~1e-3  AND  top1/top2 >= ~3x
REJECT   top1/top2 ~ 1x  (flat; e.g. P6's 1.02-1.06x, P9's loose control)

Verified ACCEPTs: P5 (1.09e-2, 7.8x), P8 (2.86e-2, 6.44x), P9 (5.3e-2, 4.5-23x).
All three also had the sampling mode and the beam decoder top-1 agree exactly;
that agreement has so far been a reliable co-indicator of correctness.
```

## 4. Consequence for P6

Two circuits recover their answers at 2e-3; P6 does not, under two very
different routers. The completed endpoints are not entanglement-limited
(`selected_absorbs_hit_max_bond = 0` on every D=512 run), but the data do not
yet exclude a P6-specific cutoff transition or trajectory interaction. The
working hypothesis is that P6's peak is weaker or more delocalised, so a
truncation loose enough to permit completion may erase it; the sub-2e-3
interval still requires a completed bisection.

**Correction (same day).** An earlier revision of this section, and of
`P6_MPO_DIAGNOSIS.md`, treated the cutoff-window hypothesis as refuted for P6.
It is not. Sections 2.1-2.3 above are measurements on **P9 and P5**; they show a
looser cutoff is not *inherently* destructive for those circuits, but say nothing
about a P6-specific transition inside 1.5e-3 < c < 2e-3.

The two sub-2e-3 P6 runs were both stopped by scheduling decisions, never by the
solver:

| cutoff | gates | why it ended |
|---|---|---|
| 1.5e-3 | 89/2593 | terminated for budget (24 h ETA vs 12 h limit) |
| 1.75e-3 | 164/2593 | terminated by operator while decaying (+120/+30/+1 per 20 min) |

So "P6 cannot complete below 2e-3" is **unproven**, and a window of the form
`c_router < c* < c_fidelity` remains possible.

One piece of evidence argues the window is narrow or absent: at 2e-3 P6's mode is
`top1/top2 = 1.02-1.06x` (completely flat) while P5 at the same cutoff gives
3.4x (degraded but clearly peaked). A circuit sitting just above a transition
would be expected to degrade partially rather than collapse totally. That argues
for bisecting downward, but a sufficiently sharp transition would look identical,
so it is not decisive.

**Open:** finish the bisection to actual stalls/completions, and test adaptive
("rescue pulse") cutoffs that pay the fidelity cost only where the router stalls
rather than across all 2593 gates.
