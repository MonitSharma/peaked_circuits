# P11 overnight plan — M3 Pro / 36 GiB, safe mode

Companion to [`P11_REASSESSMENT.md`](P11_REASSESSMENT.md). Runner:
[`scripts/p11_overnight_ladder.sh`](../scripts/p11_overnight_ladder.sh).

## The hypothesis being tested

Every historical P11 run used `--max-bond 512` (reference: 8192) and
`--cutoff 6e-4`/`1e-3` (reference: `2e-3`), most also clamped
`--unswap-trigger-max-bond 128`, and 155 of 162 capped `--max-work-gates` at
≤250. The deepest runs pinned at `peak_max_bond = 512`. If the sawtooth
(bond grows → unswapping finds the permutation → bond collapses) is being
truncated by that ceiling, raising it should change the drain depth.

**Baseline to beat: 142 / 1984 work gates.**

## Why this is safe on your machine

Measured over all 162 historical P11 runs:

| | value |
|---|---|
| peak process-tree RSS, median | 2.82 GB |
| peak process-tree RSS, p90 | 3.64 GB |
| peak process-tree RSS, **max** | **5.42 GB** |
| peak MPO size (`total_elems`), max | 2.38×10⁶ = **38 MB** |

The campaign never touched 15% of your RAM. Raising `--max-bond` should be
tested under a watchdog, but it is not literally memory-free: `--unswap-threshold`
(τ) is a trigger for starting unswapping, not a hard upper bound, and an
absorption step can overshoot it. What `max_bond` changes is the allowed
*shape*: how large the single center bond may get. The observed 1.13M-element
overshoot in the smoke test is exactly why the watchdog remains enabled.

Worst-case transient at χ=4096: one center tensor is `4 · 4096² · 16 B` =
**1.07 GB**, and a LAPACK SVD on it needs roughly 3–5× that in workspace, so
expect peak RSS in the **4–10 GB** range. The watchdog trips at **18 GB**,
leaving 18 GiB for macOS. This is a conservative operational guard, not a
proof that no larger transient can occur.

**Do not go to χ=8192 on this host.** One tensor becomes 4.3 GB and the SVD
workspace approaches 20 GB. χ=4096 is the right ceiling for 36 GiB.

## What to do

### Before you start (5 minutes, while awake)

1. **Plug in AC power.** Sustained 5-thread load for 8 hours will drain and
   thermally throttle on battery.
2. **Put the laptop on a hard surface**, lid open. Not a bed, not a couch, not
   a closed clamshell without external cooling.
3. **Freeze the solver.** Your working copy at
   `~/code_projects/qat/peaked-mpo-solver` is dirty with the research
   hardening changes. The quimb QR guard and swap-cap changes should be
   committed, while the attempted `equalize_norms_(1.0)` in-place normalization
   must remain absent: A/B testing reproduced a macOS Accelerate/BLAS SIGSEGV
   with it and a clean 100-gate probe without it. Commit the source state:

   ```bash
   git -C ~/code_projects/qat/peaked-mpo-solver add src/p9solver && git -C ~/code_projects/qat/peaked-mpo-solver commit -m "fix: avoid unsafe in-place MPO normalization"
   ```

   The script refuses to run if the unsafe normalization is present or the QR
   guard is missing.
   The ladder prefers the repository-local isolated interpreter
   `.venv-p9-isolated/bin/python`, which was created with `uv` and avoids the
   dirty solver checkout's original environment. Override it explicitly with
   `SOLVER_PYTHON=...` if you want a different environment.
4. **Quit heavy apps.** Docker, VMs, Chrome with 80 tabs. Not required — just
   removes noise from the RSS measurements.

### Stage 0 — bounded χ=4096 probe plus P9 control (~15–30 min, watch it)

```bash
STAGE0_ONLY=1 caffeinate -is bash scripts/p11_overnight_ladder.sh
```

This first probes **P9** at the loosened config (`--cutoff 0.002 --max-bond 4096`)
for eight work gates, then runs the known-good full P9 control at
`--cutoff 0.0006 --max-bond 512` with the historical P9 trigger
(`--unswap-trigger-max-bond 128`) and checks that it reproduces the known
56/56 bitstring. Two things it buys you:

- confirms the new high-bond flags are valid and measures their short-run RSS;
- confirms the solver and expected-bitstring path still reproduce P9 before P11.

A full P9 run at χ=4096 is deliberately not used as the gate: the expensive
high-bond unswap probes can make that control take much longer than the
historical χ=512 run without adding information needed before P11.

Watch Activity Monitor → Memory. Expect the memory-pressure graph to stay
green. If the full P9 control fails to reproduce, stop before going further —
the script exits rather than proceeding.

### Stage 1 — the P11 ladder (overnight, ~8 h)

```bash
caffeinate -is bash scripts/p11_overnight_ladder.sh
```

Four sequential runs, 2 h wall cap each, RSS watchdog on each, P11 blind
(`--expected-bitstring ""`) throughout:

| run | cutoff | max_bond | isolates |
|---|---|---|---|
| R1 | 2×10⁻³ | 512 | the cutoff, at your old bond |
| R2 | 6×10⁻⁴ | 4096 | the bond, at your old cutoff |
| R3 | 2×10⁻³ | 4096 | reference-like config |
| R4 | 5×10⁻³ | 4096 | argmax-only robustness (peak carries ~10% of mass, so fidelity can be poor) |

All four drop `--unswap-trigger-max-bond`, drop `--max-work-gates`, and set
τ = 10⁶ and `--abort-after-no-progress-unswap-cycles 40` (the CLI default is
**2**, which would kill a run on a two-cycle plateau).

Leave it. `caffeinate -is` keeps the machine awake without keeping the display
on. The display can sleep; the lid must stay open.

### Next morning

```bash
tail -40 ~/Code/p12-helios-recovery/results/p11_bond_ladder/*/ladder.log
```

Read `last_work_consumed` per run against the 142 baseline. The completed R3/R4
artifacts now supersede the original predictive thresholds below: R4 reached
1,984 gates without approaching the bond ceiling, while R3 reached 78 gates at
the reference cutoff.

The solver also emits `truncation_diagnostics` in each `summary.json`, which
answers the hypothesis directly:

- `rows_at_max_bond` — how many compression steps were clipped by the ceiling.
  Large on R1 (cap 512) and near zero on R3 (cap 4096) is the signature that
  the old runs were bond-starved.
- `first_stage_at_max_bond` — the work-gate index where clipping first began.
  If this is well before 142 on the D512 runs, the historical stall and the
  ceiling coincide.

| observation | reading |
|---|---|
| any run > 300 gates | treat bond capacity as non-binding for that rung; measure fidelity, truncation, and throughput before choosing hardware |
| a run completes at a loose cutoff but not at the reference cutoff | the observed tradeoff is fidelity versus throughput; map the cutoff frontier before changing hardware |
| all runs 130–160 | investigate routing and numerical trajectory, then test the official repo's TNO/distillation modes |
| all runs < 100 | something regressed vs. the historical config — diff `command.txt` against a historical `launcher_manifest.json` |
| a run trips the RSS watchdog | note which; χ=4096 is too aggressive for that cutoff, retry at 2048 |

## If you want a second night

The historical estimate is retained for provenance, but the completed R4 run
shows that runtime depends strongly on cutoff and routing trajectory. Use
[`P11_NEXT_ACTION_PLAN.md`](P11_NEXT_ACTION_PLAN.md) for the gated P9-first
cutoff study instead of selecting a rung solely by drain rate.

## What this plan will not do

It will not rule P11 out. If the ladder is flat, the remaining branches
(GPU at χ≫4096, the official repo's TNO and distillation modes, beam-search
unswapping) are still open and are cheap relative to the effort already spent.
A negative ladder narrows the cause; it does not close the problem.
