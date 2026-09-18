# P11 routing diagnosis

**Circuit:** `peaked_circuit_P11_Hqap_98x1999.qasm` — 98 qubits, SHA256
`1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`,
**1984 work gates** (`total_work_gates` reported by the solver).

**Method.** All usable prior solver trajectories (166 runs) were re-parsed and
rescored with
[`scripts/parse_routing_trajectories.py`](../scripts/parse_routing_trajectories.py),
and a controlled A/B was then run on a **clean upstream solver** at faithful
precision (this session). No expected bitstring, tracker answer, emulator
output, or leaked string is read anywhere — only solver telemetry.

Outputs under `results/p11_diagnosis/`:

- `routing_runs_summary.csv` / `routing_trajectories.csv` — the 166-run rescore.
- `ab_cap_c128_result.json` — the controlled complex128 swap-cap A/B.
- `solver_maxswap_patch.diff`, `environment_freeze.txt`, `SHA256SUMS` — freeze.

Two solver families are covered:

| Family | Engine | Runs | Bottleneck |
|---|---|---|---|
| **MPO** (`p9solver`) | midpoint MPO + greedy unswapping + SABRE routing | 157 | **routing non-convergence** (focus) |
| **MPS** (MettleQ `mps_state`) | matrix-product-*state* evolution | 9 | **entanglement / bond growth** |

> **Correction vs. the first draft of this document.** An earlier pass concluded
> that `--unswap-max-swaps-per-step` (capping swaps per unswap step) was the key
> lever, based on historical **complex64** runs that reached 196/1984 gates. A
> controlled same-solver A/B at faithful **complex128** (§2) shows the opposite:
> capping *hurts*. The complex64 result was an artefact of low precision plus a
> now-lost solver fork, not a real routing improvement. The corrected conclusion
> is below.

---

## 1. P11 MPO is routing-limited, not tensor-limited (confirmed)

Across every faithful (complex128) MPO P11 run:

- **Peak bond stays low** — typically 4–64, occasionally 256 — even after
  100–142 work gates. Contrast P9, which *succeeds* by growing to bond 512 /
  ~1e6 elements. For P9 the tensor does the work; for P11 the router spins.
- **Stage-time breakdown** (default deep runs, ≥90 gates): unswapping ≈ 44 %,
  absorb-probing ≈ 38 %, rewiring ≈ 3 %. Cost is dominated by the routing
  controller, not by large SVDs.
- **The stall is real and reproducible.** Uncapped greedy drains work to
  **~130–142 / 1984 gates** and then stops. Example
  (`cutoff0006_center035_resume250_20260816`, complex128): cycles 61→70 consume
  **0 work gates each** while `total_elems` oscillates 84k↔142k and bond sits at
  64. That is exactly "routed layers oscillate rather than drain": the greedy
  keeps applying bond-neutral swaps that never unblock the next work gate.

Because bond is low, routing dominates the objective — the regime the goal
anticipated ("Low bond → routing can dominate objective"). Tensor-side knobs
(cutoff, max_bond, compression) are **not** the binding constraint and were
correctly de-prioritised.

---

## 2. The swap-cap "lever" is a complex64 artefact (controlled A/B)

Same upstream solver (`3bcdc1e`), same config (cutoff 1e-3, max_bond 512,
unswap_threshold 875000, trigger_max_bond 128, seed 123), **complex128**, equal
3-thread budget, varying only `--unswap-max-swaps-per-step`
(`ab_cap_c128_result.json`):

| cap | cycles | wall | work-gates | peak bond | **gates / 100 s** |
|---|---|---|---|---|---|
| **unset (uncapped)** | 17 | 342 s | **46** | 8 | **13.5** |
| 4 | 7 | 252 s | 19 | 4 | 7.5 |
| 1 | 4 | 227 s | 6 | 2 | 2.6 |

The cap **monotonically hurts** at faithful precision — uncapped is ~5× faster
than `maxswap1`. The historical complex64 `maxswap1` win (196 gates) does **not**
reproduce; complex64 also *crashes* in quimb's `qr_stabilized_numba`, so that
path is both non-reproducible and numerically fragile. The knob is retained in
the patched CLI for completeness but is **rejected as a routing strategy.**

(For the historical record, the 166-run rescore still shows `maxswap1`
out-scoring the *complex64* defaults — that comparison is now understood as
precision-confounded, not a routing effect.)

---

## 3. The MPS (state) approach is entanglement-limited

The 9 MettleQ MPS runs evolve the actual state. They fail for a *different, more
fundamental* reason: bond saturates `dmax` (512/1024) within ~400–500 processed
operations with **relative discarded weight 0.03–0.6** — the truncated state is
no longer faithful. Whole-circuit routing plans ~54k swaps vs ~124k naive, so
routing is fine; the wall is genuine entanglement growth. MPS state evolution is
**not** a viable path to the full 1984 gates.

---

## 4. Route-aware machinery: tested in the wrong regime so far

The solver ships `bond_route_proxy` (+ weight / veto·hybrid·augment policy /
allow-nonbond / lookahead) and alignment scoring. Prior runs exercised them but
only reached **≤ 42–100 work gates** — i.e. the *pre-stall* region, where plain
`bond` selection already drains work and there is nothing to fix. **None of them
was ever run into the ~130–142-gate stall region where the degeneracy actually
bites.** So the existing evidence neither confirms nor refutes route-aware
scoring for the real problem; that test is the natural next experiment (§6).

---

## 5. A defensible routing-debt / progress metric

Retaining the primitives (`W` remaining work gates, `S` applied swaps/cycle,
bond, elems, per-stage times), the useful composite is a **sustained work-drain
rate**:

- **`rate_last_third_gph`** — work gates/hour over the final third of a run,
  which penalises early-fast/later-stalled trajectories as required.
- **stall flag** = last-third made < 2 gates while spending > 20 % of wall. It
  fires precisely on the ~140-gate wall and never on successful P9 (P9 drains `W`
  to 0 with rising bond).

---

## 6a. Numerical barriers removed, then a decisive crash-free 300-gate test

The first stall-region attempt was confounded by two solver crashes; both were
fixed so the stall could be measured cleanly (not as a crash artefact):

1. **quimb complex64 `qr_stabilized` crash** → guarded with a pure-numpy
   re-registration (`p9solver/_quimb_compat.py`), verified correct.
2. **complex128 inf/NaN overflow** in the compression SVD at gate ~48 — the
   absorbed operator's Frobenius norm grows geometrically and overflows. Fixed
   by rescaling each absorbed MPO to unit tensor-norm via quimb
   `equalize_norms_(1.0)` (the log-scale is tracked in `.exponent`; the peak
   bitstring `argmax_x |<x|U|0>|^2` is scale-invariant). Verified: runs now sail
   past gate 48.

With both crashes removed, a controlled 300-gate test (RANKING threshold), same
config, complex128, equal budget (`solve_*` runs + `solve_*_result.json`):

| config | outcome | work-gates | note |
|---|---|---|---|
| plain `bond` (control) | **hard stall** | **59** | +3 gates over final 30 cycles; elems oscillate at bond 16 |
| `bond_route_proxy` w2 look16 (no allow-nonbond) | stall | 85 | (earlier 200-gate run) |
| `bond_route_proxy` **allow-nonbond** hybrid w2 look16 **maxswap6** | stall | **73** | beats plain bond (past 59) but decelerates +50→+8/20cyc |
| `bond_route_proxy` allow-nonbond **augment w5** (uncapped) | **segfault** | — | applied all 49 swaps/step → bond 512 / 24M elems in one cycle |

**Two decisive findings:**

- **Greedy + every shipped route-aware machinery is inadequate.** Plain bond,
  route-proxy, allow-nonbond, veto/hybrid/augment, weight and lookahead
  variants, ± swap cap — all either **stall at 59–85 / 1984 work gates** or
  **explode**. This is the DECIDE-tree precondition that a *new controller*
  (finite-horizon beam search over routing states) is required, not more knob
  tuning.
- **Routing and entanglement are coupled.** Greedy keeps bond low precisely by
  *avoiding* the progress-enabling swaps; forcing them (allow-nonbond, augment)
  immediately grows the bond toward the 512 truncation wall (24M elements → OOM
  segfault). So P11's "low bond" is not benign headroom — it is the symptom of a
  router that has stopped making progress. This unifies the MPO stall with the
  MPS entanglement wall (§3): draining work *requires* growing entanglement, and
  the entanglement grows fast.

## 6. Earlier attempt (superseded by §6a): route-aware scoring, crash-confounded

The trajectory matches the goal's **"early improvement then oscillation"**
branch, so the prescribed first response was tested directly — uncapped
complex128, `--max-work-gates 200`, plain `bond` vs `bond_route_proxy` (weight
2.0, lookahead 16, hybrid policy), equal 5-thread budget, RSS-watchdog launcher
(`stall_control_bond_200g`, `stall_routeproxy_w2_look16_200g`;
`stall_routeproxy_result.json`):

| run | outcome | work-gates | note |
|---|---|---|---|
| plain `bond` (control) | **crashed** `exit_1` | 48 | `ValueError: array must not contain infs or NaNs` at gate ~48–50 |
| `bond_route_proxy` w2 look16 | **stalled** | 85 (62 cycles, 1809 s) | +7 gates over the final 20 cycles → oscillating, not draining |

Two conclusions:

1. **Route-aware scoring does not break the routing degeneracy.** It stalls too
   (≈85 gates, decelerating hard), just later than the crash and slower than
   plain bond. Its transient "lead" over the control was only because the
   control *crashed*, not because route-proxy drains deeper. The existing
   route-aware machinery is therefore **inadequate for the real problem** — the
   DECIDE-tree precondition for moving to beam search.
2. **A second numerical fragility exists on upstream.** Independent of the quimb
   complex64 QR crash (now guarded), plain complex128 hits `inf/NaN` at gate
   ~48. The lost fork's `rescale1e12` / `drop1e12` / `checkpointnorm` run
   variants were exactly this norm-stabilization hardening; upstream lacks it.

### Decision

Per the DECIDE tree, greedy + all shipped route-aware machinery having failed
points to **finite-horizon beam search over permutation/routing states** (keep K
best layouts per step; exact MPO evolution only for finalists), which is a
substantial new controller — and it would additionally require porting the
fork's norm-rescaling to survive past gate ~48, then many hours of checkpointed
complex128 evolution, then a non-sampling decode. That is beyond a single
session.

## 7. The barrier is intrinsic entanglement, not the routing controller

The controller experiments (§6a) could be dismissed as "just a weak controller".
They are not — the MPS *state* telemetry (`entanglement_growth.csv`, from the
MettleQ engine with near-optimal lookahead routing) shows the wall is the
**Schmidt rank of the state itself**, which no routing/ordering can remove:

| dmax | work 2q-gates | bond_max | bond_mean | rel. discarded weight |
|---|---|---|---|---|
| 512 | 60 | 2 | 1.5 | 1e-6 |
| 512 | 80 | **512 (saturated)** | 138 | **0.11** |
| 512 | 100 | **512 (saturated)** | 252 | **0.47** |
| 1024 | 60 | 4 | 1.7 | 1e-6 |
| 1024 | 76 | **1024 (saturated)** | 359 | **0.027** |

Key points:

- **Flat then explosive.** The state is essentially a product state
  (bond 2–4, discarded ~1e-6) for the first ~60 two-qubit work gates, then the
  Schmidt rank **explodes** — bond grows ≥ 256× over ~16–20 gates.
- **Doubling the bond budget is consumed entirely.** At the same depth (~76–80
  gates) the state saturates *both* 512 and 1024 and the mean bond rises 138→359.
  The true Schmidt rank therefore exceeds 1024; this is intrinsic entanglement,
  not a dmax=1024 truncation artefact.
- **Memory feasibility.** An MPS on 98 sites at bond D needs ≈ 98·2·D²·16 bytes,
  so the 36 GB host caps bond at **≈ 3390**. Discarded weight at (gate 76,
  bond 1024) is already 0.027 and rising ~4× per gate of depth; the bond required
  to hold fidelity crosses ~3390 within roughly a dozen more work gates — i.e.
  faithful representation becomes **infeasible by work-gate ≈ 90–120 of 1984
  (~5 %)**.
- **Ordering cannot save it.** MPS bond depends on qubit ordering only up to a
  bounded factor; a peaked circuit's entangled *bulk* is volume-law across
  essentially all bipartitions, so no SWAP network keeps it at feasible bond.
- **The MPO picture agrees.** Forcing the operator to make progress (§6a,
  allow-nonbond/augment) drives its bond straight to 512 / 24M elements and
  segfaults — the operator entanglement explodes exactly like the state's.

This is the genuinely demonstrated computational barrier: **P11's state and
operator entanglement provably exceed a 36 GB tensor-network representation
within ~5 % of the circuit depth, independent of the routing controller.** A
better controller (beam search, dynamic MPS scheduling) changes *when* the
constant-factor wall is hit by a few gates; it cannot change the exponential
growth of the Schmidt rank through the circuit's entangled bulk.

### 7a. The full-network-contraction fallback is also closed

The DECIDE tree's last resort is full tensor-network contraction (cotengra /
TTN / hybrid) of the amplitude `<x|U|0>`, which sidesteps running-state
entanglement. It does not help here — the P11 interaction graph is dense and
long-range (2q-gate index-distances span 1–96, effectively all-to-all), so its
contraction is high-treewidth (`contraction_width_result.json`):

- The full amplitude tensor network (5703 tensors after simplification) has a
  **greedy contraction width of 2^202** (largest intermediate 2^202 ≈ 1e50 TB) —
  vs the 36 GB cap of **2^31.1**. Greedy is a loose upper bound, but a
  quality-optimized path (`HyperOptimizer`, `minimize='size'`) failed to converge
  in > 15 min of search, consistent with a large optimal treewidth for a dense
  98-qubit circuit. Either way the amplitude contraction is many orders of
  magnitude beyond the host.

So all three tensor-network routes — MPS state evolution (MettleQ's method),
MPO operator compression (`p9solver`), and full-network contraction — are
demonstrably infeasible on this host. The goal's own caution applies exactly:
"Do not assume random connectivity makes generic contraction easy."

### Honest status on the full solve — demonstrated barrier

No blind 98-bit peak candidate has been produced, and none is fabricated. After
**removing both numerical crashes** (§6a), the barrier is demonstrated cleanly
(not as a crash artefact) on multiple independent axes, on the M3 Pro / 36 GB
host with the only surviving (upstream) solver:

- **Routing degeneracy (crash-free):** greedy `bond` drains to **59 / 1984**
  gates then hard-stalls (+3 gates / 30 cycles) with bond stuck at 16.
- **All shipped route-aware machinery fails the same way** — stalls at 73–85
  gates, or (augment, high weight) explodes to bond 512 / 24M elements and
  segfaults (§6a).
- **Routing⇄entanglement coupling:** the low bond is the *symptom* of a stalled
  router; forcing progress grows the bond straight to the truncation wall.
- **MPS entanglement wall** at < 5 % of ops — the operator picture and the state
  picture hit the same physics.
- **Precision trap:** the fast complex64 path is a low-fidelity artefact, not a
  real speedup (§2).

The decisive point is §7: the wall is **intrinsic entanglement**, not the
controller. The state saturates both bond-512 and bond-1024 MPS by work-gate
~76–80 with rising truncation error, and the memory model caps the 36 GB host at
bond ≈ 3390 — reached within ~5 % of the circuit. A better controller (the
DECIDE-tree's beam search / dynamic-MPS tiers) can only shift the constant-factor
wall by a few gates; it cannot bend the exponential Schmidt-rank growth. **On
this M3 Pro / 36 GB host, a faithful classical tensor-network solve of P11 is
therefore not achievable, and no blind 98-bit candidate can be produced without
larger hardware or a fundamentally different (non-tensor) method.** None is
fabricated. The harness (RSS-watchdog launcher, deterministic manifests, QR
guard, norm rescaling, freeze) is preserved so the run can be resumed on a
machine whose memory admits bond ≫ 3400.

### Reproducibility / safety

- Solver: clean upstream `alexgalda-m/peaked-mpo-solver` `3bcdc1e` +
  `solver_maxswap_patch.diff` (adds the `--unswap-max-swaps-per-step` knob and a
  **quimb complex64 `qr_stabilized` crash guard**, `p9solver/_quimb_compat.py`).
- Launcher: [`scripts/run_p11_mpo.py`](../scripts/run_p11_mpo.py) adds a
  **process-tree RSS watchdog** (default 30 GB on the 36 GB M3 Pro),
  deterministic thread budget, and a per-run manifest (circuit SHA256, solver
  commit + dirty flag, options, environment).
- Environment: `environment_freeze.txt` (python 3.10.16, numpy 2.2.6, scipy
  1.15.3, numba 0.65.0, quimb 1.11.2, qiskit 1.4.5). Checksums in `SHA256SUMS`.
- The lost fork (`55be6eb`, `a850c79`, with `p11_blind_prefix` runner, `--dtype`,
  checkpoint/resume) is **not on disk**; only the reconstructed lever above.
