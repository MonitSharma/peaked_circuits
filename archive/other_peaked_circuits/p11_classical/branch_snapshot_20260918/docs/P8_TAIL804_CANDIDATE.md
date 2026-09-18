# P8 SOLVED — tail materialization at 804/808

> **VALIDATED 2026-09-01.** The candidate below is the correct P8 answer,
> confirmed externally after being frozen answer-blind. P8 is solved.

**Candidate**

```
1000011001010101101111011100000111000111
```

SHA256 `bbeaf77f910d073620090714d4b780e469602f985ff0f919fb42689493f6b8f4`.
Frozen answer-blind at `results/p5_p6_p8_recovery/P8/tail804_7296a2a/P8_CANDIDATE_FREEZE_TAIL804.json`
before any evaluation.

## How it was obtained

Solver `peaked-mpo-solver-p8-beam` at **`7296a2a`** (clean worktree), conda
`p9-openblas`, with the settings recovered in
`docs/P8_804_FORENSIC_RECONSTRUCTION.md` plus tail materialization:

```
--max-bond 512 --cutoff 0.0006 --unswap-threshold 500000 --seed 2024
--sabre-trials 90 --post-sabre-trials 50
--route-candidates 4 --route-score bond_profile --route-score-lookahead 8
--route-seed-stride 1009 --center-ratio 0.5 --absorb-score total_elems
--unswap-select-mode bond --max-its 20 --flip-freq 2
--abort-after-no-progress-unswap-cycles 60
--tail-materialize --tail-limit 8
--materialize-max-bond 512 --materialize-cutoff 0.0006
--samples 1000 --decoder beam --decoder-beam-width 8
```

The compression reproduced the 804 trajectory exactly (804 at cycle 70, abort at
cycle ~131, final bond 105, final elems 215604, leftover L=2/R=17), then the
guard fired and `TAIL_MATERIALIZE` triggered with `remaining_work_gates = 4`.

## Why the abort is the trigger, not a failure

`cli.py:1076` evaluates eligibility **after** the compression loop exits:

```python
tail_materialize_eligible = bool(
    args.tail_materialize
    and remaining_work_gates is not None
    and remaining_work_gates <= args.tail_limit)     # 4 <= 8
...
elif terminal_failure and not tail_materialize_eligible:
    summary["sampling_skipped_reason"] = ...
```

The `and not tail_materialize_eligible` clause is what allows an aborted run to
materialize when few enough work gates remain. There is no race with the
no-progress guard.

## This is a full-circuit result, not a truncated one

`mpo_to_mps(mpo, layers_left[:-2], layers_right, ...)` applies the residual
layers before the compressed core (`pipeline.py:2760` loops the passed layers,
2766 applies the core). The 2 left and 17 right leftover layers -- which contain
the 4 unabsorbed work gates -- are folded in during materialization. This is the
same code path and the same `[:-2]` convention that produced the verified
**56/56 on P9** and **44/44 on P5**.

So the 4 remaining gates were applied, by materialization rather than by the
unswap loop. The candidate is a complete P8 simulation.

## Fidelity metrics against the verified calibration

| metric | **P8 (this)** | P5 (verified 44/44) | P9 (verified 56/56) | known-failure |
|---|---:|---:|---:|---:|
| sample peak fraction | **0.038** | 0.012 | 0.048-0.098 | 0.001 |
| decoder top-1 probability | **2.86e-02** | 1.09e-02 | 5.3e-02 | 4.9e-09 |
| top1 / top2 | **6.44x** | 7.8x | 4.5-23x | ~1.0x |
| unique samples | 933/1000 | 973/1000 | 676-829/1000 | 1000/1000 |

Peak count 38 versus 4 for the runner-up. **The sampling mode and the beam
decoder top-1 agree exactly** -- two independent extraction paths over the same
MPS converging on the same 40-bit string.

This is the first P8 result in the campaign to pass the promotion bar
(`docs/PEAKED_FIDELITY_CALIBRATION.md`) rather than fail it. Every earlier
candidate-producing route was rejected for flat modes (top1/top2 ~ 1.0),
negative probabilities, non-convergence, or truncation artifacts.

## Do not misread `matches_expected_bitstring: false`

`--expected-bitstring` defaults to `DEFAULT_EXPECTED_P9`, so `summary.json`
compares this 40-bit P8 string against P9's 56-bit answer. The `false` is a
flag-default artifact and carries no information. Pass
`--expected-bitstring ""` to disable the comparison in future runs.

## Status and what remains unverified

**Status: `EXTERNALLY_VALIDATED`.** The candidate is the correct P8 answer.

The internal fidelity metrics predicted this correctly: every gate calibrated on
P5 and P9 passed, and the two independent extraction paths agreed. No external
information was used at any point before the freeze.

Convergence and seed-reproducibility runs were planned but are unnecessary now
that the answer is confirmed. The originally planned "residual ladder" at
D=512/1024/2048/4096 was moot regardless: `mpo_to_mps` had already applied the
4 remaining work gates.

## Artifacts

`results/p5_p6_p8_recovery/P8/tail804_7296a2a/` -- `summary.json`, `stats.json`,
`stats.csv`, `samples.tsv`, `run.log`, and the candidate freeze. No `mpo_dump.pkl`
was produced: materialization proceeded directly to an MPS and sampled, so there
is no separate state pickle to transfer.
