# P11 — where we are and what to try next

One-page orientation for anyone picking this up. Full evidence:
[`P11_ROUTING_DIAGNOSIS.md`](P11_ROUTING_DIAGNOSIS.md); data in
`results/p11_diagnosis/`.

## The problem

Classically find the peak 98-bit output of `peaked_circuit_P11_Hqap_98x1999.qasm`
(SHA256 `1373d50c…`, 98 qubits, **1984 two-qubit "work" gates**), blind — no
oracle, tracker answer, emulator output, or leaked bitstring. Two engines exist:

- **MPO + greedy unswap** (`qat/peaked-mpo-solver`, `p9solver`) — the method that
  *solves* P9 (56 qubits, bond 512).
- **MPS state evolution** (`Qupertino/src/mettleq`, MettleQ) — dynamic per-gate
  routing.

## What we established (measured, reproducible)

1. **Faithful greedy MPO routing stalls at ~59 / 1984 work gates** (bond 16,
   `elems` oscillate, 0 gates/cycle). Original "routing non-convergence"
   diagnosis confirmed.
2. **No shipped route-aware knob fixes it.** `bond_route_proxy`, veto/hybrid/
   augment, `allow_nonbond`, weight/lookahead sweeps, ± swap cap — all stall at
   59–85 gates or **explode** (augment+high-weight → bond 512 / 24M elems →
   segfault). See §6a of the diagnosis.
3. **The swap-cap "win" was a complex64 artefact**, not a real lever — at faithful
   complex128 the cap *hurts* (uncapped 46 gates > cap-4 19 > cap-1 6). See §2.
4. **Root cause = routing⇄entanglement coupling.** Greedy keeps bond low by
   *avoiding* progress-enabling swaps; forcing them grows the bond straight to the
   truncation wall. Low bond is the symptom of a stalled router, not headroom.
5. **Intrinsic entanglement barrier (controller-independent).** The MPS state
   saturates *both* bond-512 and bond-1024 by work-gate ~76–80 (discarded weight
   0.11 and 0.027 respectively; doubling the budget is fully consumed → true
   Schmidt rank > 1024, still climbing). A 98-site MPS caps at **bond ≈ 3390** in
   36 GB, reached within ~5 % of the circuit. See §7 + `entanglement_growth.csv`.
6. **Full-network contraction (cotengra/TTN) is also infeasible** — dense
   long-range circuit (2q distances 1–96), greedy contraction width **2^202** vs
   the 2^31 memory cap. See §7a + `contraction_width_result.json`.

**Conclusion:** on an M3 Pro / 36 GB host, a faithful classical tensor-network
solve of P11 is not achievable, and no defensible blind 98-bit candidate can be
produced here. This is the expected outcome for a 98-qubit quantum-advantage
circuit (P9 at 56q is simulable; P11 is past the line for this hardware).

## Engineering fixes made (in `solver_maxswap_patch.diff`, apply to upstream `3bcdc1e`)

- **quimb complex64 QR crash guard** (`p9solver/_quimb_compat.py`) — was killing
  long runs mid-flight.
- **complex128 norm-overflow fix** — rescale absorbed MPO to unit norm via
  `equalize_norms_(1.0)` (peak is scale-invariant); prevents the inf/NaN crash at
  gate ~48.
- **`--unswap-max-swaps-per-step`** knob (kept for completeness; shown unhelpful).
- **`scripts/run_p11_mpo.py`** — reproducible launcher with process-tree RSS
  watchdog + deterministic manifest.

## What to try next (only with more resources)

Ordered by expected value; **none is worth running on 36 GB** — all need the
entanglement headroom that this host lacks:

1. **Bigger memory** (≥ ~1 TB) to push MPS/MPO bond past ~3400 and re-measure the
   entanglement peak. If the peak bond stays < a few 10⁴ the circuit becomes
   simulable; the growth curve in `entanglement_growth.csv` says it likely will
   not.
2. **Finite-horizon beam search over routing states** (the DECIDE-tree next tier):
   keep K best layouts/permutations per step, exact MPO evolution only for
   finalists, with an adaptive tensor penalty as bond rises. Shifts the wall by a
   few gates at best given finding #5 — implement only alongside #1.
3. **Structure-exploiting / non-tensor methods** — the peaked circuits are built
   with hidden structure; a blind method that recovers partial structure (not a
   full contraction) is the only route that sidesteps the entanglement wall.

## Reproduce the diagnosis

```bash
# rescore every run dir into the two CSVs
python scripts/parse_routing_trajectories.py \
  --roots . results/p11_research results/p9_optimization \
  --summary-csv results/p11_diagnosis/routing_runs_summary.csv \
  --trajectory-csv results/p11_diagnosis/routing_trajectories.csv
```
