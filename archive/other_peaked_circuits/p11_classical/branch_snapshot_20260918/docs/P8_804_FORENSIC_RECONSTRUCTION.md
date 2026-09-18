# P8 804/808 forensic reconstruction

> **RESOLVED 2026-08-31 — the 804 trajectory has been reproduced exactly.**
> The "Decision" and "Final provenance update" sections below are **superseded**;
> they were written on three factual errors, each corrected in §Resolution at the
> end of this document. The run is reproducible at solver commit `7296a2a`, and
> all six recorded state fields match bit-for-bit.

## Objective

The highest-value remaining experiment in the old MPO family is not another
parameter sweep. It is to reproduce the historical `flip_freq=2` trajectory
that consumed 804 of 808 work gates, stop before the next unswap cycle, and
serialize the live MPO for a four-work-gate residual solve.

## Settings recovered from the committed campaign artifacts

The exact recorded 804 campaign entry is:

| setting | recovered value |
|---|---:|
| qubits / work gates | 40 / 808 |
| max bond | 512 |
| cutoff | 0.0006 |
| seed | 2024 |
| initial SABRE trials | 90 |
| post-SABRE trials | 50 |
| route candidates | 4 |
| route score | `bond_profile` |
| route lookahead | 8 |
| route seed stride | 1009 |
| center ratio | 0.5 |
| absorption score | `total_elems` |
| unswap selection | `bond` |
| unswap threshold | 500000 |
| flip frequency | 2 |
| max iterations | 20 |
| no-progress guard | 60 cycles |
| decoder | beam, width 8 |
| samples requested | 1000 |
| threads | 3 |
| RSS soft/hard limits | 20 / 24 GiB |

The campaign state records:

```text
last_work_consumed: 804
termination_reason: no_progress_cycle_limit
final_max_bond: 105
final_total_elems: 215604
peak_max_bond: 272
peak_total_elems: 688728
```

The 804 result is therefore a terminal controller state, not a sampled answer.
Sampling was skipped because the no-progress guard fired.

## What provenance is available

The committed launcher manifest identifies the solver as:

```text
/Users/monitsharma/code_projects/qat/peaked-mpo-solver-p8-beam
```

and records a macOS arm64 runtime with Python 3.10.21, NumPy 2.2.6, SciPy
1.15.2, Quimb 1.11.2, Qiskit 1.4.5, and three numerical threads. The P8 QASM
hash is:

```text
ba42c338478fdfbc0241ec2289b3159bfde5dffc71603ac588ec0755fba1a484
```

The manifest does not record the solver Git SHA. It records the launch
parameters and output path, but not a complete patch archive of the dirty
solver worktree.

## Forensic checks performed

The local repository contains the compact campaign summaries, launcher
manifests, statistics, patches, and the 804 `CAMPAIGN_STATE.json`. The HPC
host contains several copies of `peaked-mpo-solver`, but none is an exact,
cleanly identified match to the macOS path in the 804 manifest:

- the P11-era HPC copy is detached at `3bcdc1e` and has uncommitted solver
  modifications plus a local compatibility patch;
- the P8-tail copy is a heavily modified dirty tree at `47c8057`;
- another HPC copy is on `codex/hpc-qr-guard-fix` at `06e6680`;
- the available upstream copy is on `main` at `47c8057`.

The named historical revisions `e1a6eef` and `7296a2a` are referenced by the
reports, but are not present as objects in this repository's Git database, and
the available HPC solver copies do not provide a verified match. The exact
uncommitted files from the original macOS worktree are also not present in the
committed manifest.

## Decision

An exact reproduction cannot responsibly be launched from the currently
available evidence. Re-running the recovered flags against one of the HPC
copies would test a different solver revision and could not establish whether
the 804 trajectory was reproduced.

The missing item is an archive or checkout of the original
`peaked-mpo-solver-p8-beam` worktree, including its Git metadata and local
modifications. Once supplied, the reproduction should:

1. verify the QASM hash and all runtime versions;
2. apply the exact worktree and launch settings above;
3. stop immediately when `last_work_consumed == 804`;
4. serialize `mpo_dump.pkl`, residual layers, routing permutation, and factor
   interface before any additional unswap cycle;
5. inspect the four remaining work gates and their active qubit component;
6. try only the isolated residual solver at D=512, 1024, 2048, and 4096.

Until the original solver worktree is recovered, Route 1 is provenance-blocked,
not algorithmically falsified.

## Final provenance update

The user has confirmed that the historical Mac checkout does not exist. The
804/808 execution therefore cannot be reconstructed exactly from the available
repository, HPC copies, or committed campaign artifacts. The recorded settings
remain valuable as a reproducibility specification, but any new run from the
current repository must be labeled a new experiment rather than a replay.


---

# Resolution (2026-08-31): reproduced exactly at `7296a2a`

## What was wrong in the analysis above

Three blocking claims were checked and all three were incorrect:

| claim above | finding |
|---|---|
| "`e1a6eef` and `7296a2a` ... are not present as objects in this repository's Git database" | Correct but misleading. They are commits in the **solver** repo (`peaked-mpo-solver`), not in `p12-helios-recovery`. Both resolve: `git cat-file -t e1a6eef` -> `commit`. |
| "The manifest does not record the solver Git SHA." | It does. `results/p5_p6_p8_recovery/P8/flip_freq_20260830_082118/p8_d512_c6e4_bp_seed2024_flip2/launcher_manifest.json` records `solver_git_commit=e1a6eef36e71816c08da1d9a9319195db3d98baf`, `solver_git_dirty=True`, and `solver_root=/Users/monitsharma/code_projects/qat/peaked-mpo-solver-p8-beam`. |
| "the historical Mac checkout does not exist" | It exists. The worktree is still on disk, **clean**, on branch `codex/p8-gate-unlock-beam` at `7296a2a`. |

## What the dirty state actually was

`e1a6eef` (2026-08-30 01:05) still hard-codes `flip_freq=None` in `cli.py` and
exposes **no** `--flip-freq` flag. The flip-frequency campaign therefore could
not have run on the committed code -- the uncommitted modification recorded as
`dirty=True` *was* the `--flip-freq` exposure. Those edits were committed later
the same day as `7296a2a` (18:08, "Add P8 tail materialization and record
controller results"), which adds `--flip-freq` at `cli.py:340` and the
supporting `active_flip_freq()` logic in `pipeline.py:1862-2086`.

`7296a2a` also introduces `--flip-schedule` and `--late-gate-beam`, but both
default off (`None` / `False`), so `--flip-freq 2` alone follows the original
path.

## The reproduction

Run `p8_repro804_7296a2a`, solver root `peaked-mpo-solver-p8-beam` at `7296a2a`
(clean), conda `p9-openblas`, using the exact settings recovered above.

| field | recorded 804 | reproduction | match |
|---|---:|---:|:--:|
| `last_work_consumed` | 804 | 804 | yes |
| `termination_reason` | `no_progress_cycle_limit` | `no_progress_cycle_limit` | yes |
| `final_max_bond` | 105 | 105 | yes |
| `final_total_elems` | 215604 | 215604 | yes |
| `peak_max_bond` | 272 | 272 | yes |
| `peak_total_elems` | 688728 | 688728 | yes |

Additionally: `leftover_left_layers = 2`, `leftover_right_layers = 17`,
wall 3081 s. Six independent quantities matching to the digit is a trajectory
replay, not a coincidence.

Artifact: `results/p5_p6_p8_recovery/P8/repro804_7296a2a/`.

## What this does and does not establish

**Does:** 804/808 is a *reproducible checkpoint*, not an unrepeatable historical
artifact. Route 1 is **not** provenance-blocked. The reproduction specification
in this document is now executable rather than hypothetical.

**Does not:** solve or explain the attractor. The reproduction terminated on the
same no-progress guard, at the same state, for the same reason. What is
recovered is a trustworthy starting point, not progress past it.

## Consequence for the earlier tail-materialization attempts

The clean tail-materialization runs that stopped at 781/808 and 782/808 started
from checkpoints produced without the flip-freq path. They should be re-run from
this reproducible 804 checkpoint instead.

## Next step (unblocked, not yet run)

Serialize at 804 before the next unswap cycle. `7296a2a` already ships
`--tail-materialize` and `--tail-limit`, so no new code is required:

1. re-run the settings above with tail materialization armed to fire at 804;
2. serialize the MPO core, residual layers, routing permutation, and factor
   interface;
3. attack the residual -- **4 work gates, 17 routed layers** -- at D = 512,
   1024, 2048, 4096. Bond dimensions that are hopeless on the full circuit are
   affordable on a 4-gate tail.

Approximately 50 minutes to reach 804, then the dump.
