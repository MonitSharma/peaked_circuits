# P11 reassessment: the classical no-go is premature

> **Update:** This is the original reassessment record. The later R3/R4
> measurements supersede its untested-resource assumptions: R4 completed all
> 1,984 P11 work gates at cutoff `5e-3`, peak bond 605, and zero bond-cap rows;
> R3 at cutoff `2e-3` reached 78 gates under the wall cap. The current plan is
> therefore a P9-calibrated fidelity/throughput frontier, documented in
> [`P11_NEXT_ACTION_PLAN.md`](P11_NEXT_ACTION_PLAN.md).

**Date:** 2026-08-24
**Scope:** audit of the `p11_classical` branch (HEAD `e60c6b7`) against the
published reference method and current literature.
**Verdict:** the branch's `P9_METHODS_EXHAUSTED` conclusion is **not supported
by its own evidence**. The dominant failure mode is a hyperparameter and budget
mismatch against the reference implementation, not a physical barrier.

---

## 1. What the branch established

Five campaigns, all ending in a documented no-go:

| Campaign | Verdict | Artifacts |
|---|---|---|
| Routing diagnosis (166 runs rescored) | "intrinsic entanglement barrier" | `results/p11_diagnosis/` |
| Low-bond MPS distillation | P9 Gate A NO-GO (36/56 bits at D=16, declining with D) | `results/p11_distillation/` |
| HQAP structural unscrambler | P9 Gate A NO-GO (mapping stability ~0.02) | `results/p11_unscrambler/` |
| Compiler attack (BQSKit/PyZX/QCEC/DDSIM) | 2/60 patches, ~2% gate reduction | `results/p11_compiler_attack/` |
| Final classical campaign | `P9_METHODS_EXHAUSTED` | `results/p11_final_campaign/` |
| HPC campaign | **written, never executed** | `hpc/`, `scripts/run_p11_hpc_campaign.py` |

The methodology is sound in every respect that matters for integrity: P11 stayed
blind throughout, artifacts are checksummed, no candidate bitstring was
fabricated, and negative results were reported honestly. Nothing below is a
criticism of the discipline. The problem is the conclusion drawn from the data.

---

## 2. Three claims in the diagnosis that do not hold

### 2.1 Every P11 MPO run was clipped at 1/16 of the reference bond ceiling

Kremer & Dupuis (arXiv:2604.21908, Appendix A.4) run this exact algorithm at:

| Parameter | Reference | This branch |
|---|---|---|
| SVD cutoff `ε` | **2×10⁻³** | 6×10⁻⁴ (116 runs) or 1×10⁻³ (37 runs) |
| Max bond `χ_max` | **8192** | **512** (151/153 MPO runs; rest 256) |
| Unswap threshold `τ` | 10⁶ | 8.75×10⁵ (143 runs) |
| Max unswap iterations | 20 | 20 (default) |

From `results/p11_diagnosis/routing_runs_summary.csv`, 162 P11 runs:

- `max_bond` was **never** 1024, 2048, 4096, or 8192.
- `cutoff` was **always tighter** than the reference, never looser.
- `max_work_gates ≤ 250` in 155 of 162 runs; only 7 allowed 1000; none uncapped.

These are the `p9solver` CLI defaults (`src/p9solver/cli.py:303-304`), tuned for
the 56-qubit laptop benchmark. `pipeline.py:1328` still carries `max_bond=8192`
internally — the CLI overrides it down to 512. Every P11 run silently inherited
a P9-shaped ceiling.

The deepest-draining runs **pinned against that ceiling**: `peak_max_bond = 512`
at 132–142 work gates. Several also set `--unswap-trigger-max-bond 128`, forcing
an unswap cycle the moment any bond passed 128 — a second, tighter clamp on top
of the first.

This matters mechanistically. The paper describes the contraction as a
**sawtooth**: bond grows during absorption, then unswapping identifies a hidden
permutation and collapses it. Capping the bond truncates the up-swing, so the
unswapper never accumulates the operator structure it needs to detect the
permutation. That is a complete and sufficient explanation for the observed
failure signature in §1 of `P11_ROUTING_DIAGNOSIS.md` — cycles that "drain 0
work gates while `elems` oscillate 84k↔142k".

### 2.2 The "explosion to OOM" is a library crash, not memory exhaustion

`P11_ROUTING_DIAGNOSIS.md` §6a reports the `allow_nonbond augment w5` policy
"exploding to bond 512 / 24M elems → **segfault**", read as an out-of-memory
event and used as evidence of an entanglement wall.

24×10⁶ complex128 elements is **384 MB**, on a 36 GiB machine. Measured across
all 162 P11 runs:

- peak process-tree RSS: **median 2.82 GB, p90 3.64 GB, max 5.42 GB**
- peak MPO size (`peak_total_elems`): median 1.28×10⁶, max 2.38×10⁶ (**38 MB**)

The campaign never used more than **15% of available RAM**. There is no memory
wall in this data. The segfault is a quimb/numba fault and should be treated as
a bug to fix, not as a resource limit — and until it is fixed it is masking
whichever unswap policy might actually work.

### 2.3 §7's entanglement wall is measured on the wrong object

The bond-3390 memory model and the `entanglement_growth.csv` saturation at work
gate 76–80 are measurements of **MPS state evolution** — propagating the full
state through the middle of the circuit.

That is precisely the object the mirror construction is designed to make hard,
and it is **not what the working method computes**. The midpoint-MPO method
works because the two mirror halves partially cancel into the operator between
them; Kremer & Dupuis state it directly: *"as long as the circuit is built from
a mirror structure, the two halves will partially cancel during contraction."*
That cancellation only becomes visible deep into the contraction. These runs
stopped at 142 of 1984 work gates — roughly 7%.

The MPO telemetry in fact shows the **opposite** of an entanglement wall: bond
stayed in the 64–512 range throughout, and the total operator never exceeded
38 MB. Section 7 generalises a measurement of the MPS route into a claim about
the MPO route, and the two do not share a bottleneck.

### 2.4 Scale of the attempt

- Longest single P11 run: **29 minutes**.
- Total P11 compute across all 162 runs: **10.2 hours**.
- P9, which *succeeds* on this same machine, takes 12–22 minutes and consumes
  1885 of 1917 work gates.

P11 was never given more than a P9-sized budget, on a problem with roughly 1.8×
the SWAP burden and 1.75× the sites.

### 2.5 What does hold

§7a (full amplitude contraction) looks genuinely closed. The P11 interaction
graph is dense and long-range, greedy contraction width is 2^202 against a 2^31
host cap, and no realistic cotengra tuning closes 170 orders of magnitude. That
branch can stay shut.

---

## 3. Where P11 sits in the literature

- **P9 (56q, H2) was broken.** Kremer & Dupuis, single A100 80 GB, 4059 s
  ([arXiv:2604.21908](https://arxiv.org/abs/2604.21908), tracker submission
  #106). The `alexgalda-m/peaked-mpo-solver` fork used here reproduces it in
  **734 s on an Apple Silicon laptop CPU** — a genuine improvement in compute
  class over the published result.
- **Nobody has published a break of the 98-qubit instances.** The IBM paper
  covers only P9 and explicitly does not analyse larger HQAP. P11 and P12 are
  the Helios-generation circuits ([arXiv:2511.05465](https://arxiv.org/abs/2511.05465))
  and sit at the open research frontier. Not solving P11 is not a personal
  failure; it is an unsolved problem.
- **The construction is unchanged in kind.** BlueQubit's HQAP recipe
  ([arXiv:2510.25838](https://arxiv.org/abs/2510.25838)) is still
  shallow-trained seed + obfuscating permutation + mirror. P11 is still a mirror
  circuit, so the structural precondition for unswapping still holds.
- **The peak may be *weaker* at 98 qubits.** The peaked-generation landscape
  paper ([arXiv:2608.11890](https://arxiv.org/html/2608.11890)) finds all
  optimizers lose a factor ~1.3 per qubit in achievable peak weight, and
  criticises the n=50 extrapolation in Aaronson–Zhang as unsupported. A weaker
  peak is harder for the QPU to demonstrate but does not make the circuit
  harder to contract — and a shallower-trained seed is *easier* to distill.
- **Two reference methods were never tried.** The official repo
  ([d-kremer/peaked-circuit-simulation](https://github.com/d-kremer/peaked-circuit-simulation))
  ships three algorithms: MPO+unswapping, **TNO contraction**, and
  **distillation** (48q / 5096 CZ in ~6 min on one GPU). Only the first was
  attempted here, and via a third-party P9-specialised fork. Note that the
  repo's "distillation" is a *different algorithm* from the low-bond MPS
  distillation attempted in `results/p11_distillation/`.

---

## 4. Structural measurements on the circuits

Measured directly from the tracker QASM files:

| | P9 | **P11** | P12 |
|---|---|---|---|
| qubits × 2q gates | 56 × 1917 | **98 × 1999** | 98 × 2457 |
| 2q gate type | `rzz` | `cz` | `cz` |
| 2q circuit depth | 103 | **115** | 175 |
| 2q gates **per qubit** | 68.5 | **40.8** | 50.1 |
| distinct qubit pairs used | 1069 / 1540 | 1356 / 4753 | 1648 / 4753 |
| mean \|i−j\| | 18.8 | 31.9 | 31.2 |
| max \|i−j\| | 55 | 96 | 97 |
| positionwise reversed-mirror match | 3/958 | 0/999 | 0/1228 |

Reading:

- P11 is only **12% deeper** than P9 in two-qubit depth, and carries **40% fewer
  two-qubit gates per qubit**. Per-qubit, it is a *lighter* circuit.
- The added difficulty is **width and SWAP overhead** — 98 sites, mean
  interaction distance 31.9 vs 18.8, so mapping all-to-all onto a line costs
  roughly 1.8× the SWAPs. That is a routing/compilation cost, not an
  entanglement cost.
- The permutation obfuscation is confirmed present: zero positionwise mirror
  match at the naive midpoint in all three circuits. This is expected and is
  exactly what unswapping exists to undo — it is not evidence against the
  method.

---

## 5. Ranked remaining options

1. **Rerun the reference algorithm at reference hyperparameters.** Raise
   `--max-bond` toward 4096, loosen `--cutoff` to 2×10⁻³, set
   `--unswap-threshold 1e6`, drop `--unswap-trigger-max-bond`, remove the
   work-gate cap. This is the single most obvious untested thing and costs one
   night. See `docs/P11_OVERNIGHT_PLAN.md`.
2. **Loosen, do not tighten.** Only `argmax` is needed and the peak carries
   ~10% of the mass, so a low-fidelity contraction still returns the right
   bitstring. Every instinct in the campaign pushed toward more accuracy
   (6×10⁻⁴ vs the reference 2×10⁻³); the correct direction is less.
3. **Run the official repo**, including its TNO and distillation modes, neither
   of which has been applied to P11.
4. **Rent a GPU.** An A100 80 GB is ~$1.50/hr; a full P11 attempt at proper bond
   is perhaps $50–200 of compute. That is the configuration the published result
   required, and it lifts the χ ceiling to ~3500 on 98 sites.
5. **Fix the segfault** in the `allow_nonbond`/`augment` unswap policies before
   drawing any conclusion from them.
6. **Beam-search unswapping** (`src/p12_recovery/real_mpo_beam.py`) — but only
   after 1–2, since a bond-starved unswapper will look inadequate regardless of
   the controller.

---

## 6. Bottom line

What the `p11_classical` branch actually demonstrates is that **the reference
method, run at 1/16 the reference bond ceiling with a 3× tighter cutoff, a
secondary bond clamp at 128, and a 29-minute budget, does not solve a 98-qubit
peaked circuit.** That is a real result about a configuration. It is not a
result about P11.

The honest status is: **unknown, and cheaply testable.** P11 may still be out of
reach — 98 qubits may need χ beyond one GPU, and the unswapper may simply fail
to locate the permutation at this width. But the branch's own data does not show
that, and the experiment that would show it has not been run.

Whatever settings crack P11 apply directly to P12 (98 × 2457), which is the same
family.

---

## 7. Provenance

- P9 SHA256 `cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35`
- P11 SHA256 `1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`
- Solver: `alexgalda-m/peaked-mpo-solver` `3bcdc1e` + local hardening
  (quimb QR guard, `equalize_norms_(1.0)` overflow fix, `--unswap-max-swaps-per-step`)
- Host: Apple M3 Pro, 12 cores (6P+6E), 36 GiB
- No P11 answer, tracker submission, emulator output, or hardware result was
  read in producing this document. All numbers come from committed artifacts,
  the tracker QASM inputs, and public literature.
