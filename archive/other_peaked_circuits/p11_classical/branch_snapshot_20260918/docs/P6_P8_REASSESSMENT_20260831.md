# P6/P8 reassessment — 2026-08-31

This is an answer-blind audit of the P6 and P8 work in this repository.  The
bitstrings supplied in the diagnosis documents are used only for post-hoc
comparison; they were not read by the simulations below.

## Runtime finding: the repeated Python failure is a native-library crash

The repository already records that `.venv-p9-isolated` (Python 3.10.16,
SciPy 1.15.3, Accelerate-backed NumPy) can segfault at D=512.  A historical
P5 run has `termination_reason: exit_-11` with no Python traceback and only
1.116 GB RSS, which is a native SIGSEGV rather than a Python exception.  The
Quimb message `Internal algorithm failed to converge; falling back to scipy
gesvd` is a recoverable warning, not the crash.

The validated MPO runs use `~/.conda/envs/p9-openblas` (Python 3.10.21,
SciPy 1.15.2, Quimb 1.11.2). For direct imports from outside the solver
checkout, point Numba at a real writable cache directory:

```bash
export NUMBA_CACHE_DIR=/private/tmp/numba-cache-p9
```

If a caller cannot provide a writable cache, disabling Numba caching is a
fallback, but it is not required by the launcher.

The new conda P8 runs produced no spontaneous crash.  Their `keyboard_interrupt`
records are intentional stops made after the endpoint was no longer improving.

I hardened `scripts/run_p11_mpo.py` and `scripts/p11_overnight_ladder.sh` to
choose a real writable Numba cache directory automatically.  A one-gate smoke
run in the conda environment completed successfully after that change
(`results/new_runtime_preflight_20260831/`).

## P6

### What has been tried

* Identity/heavy-greedy/spectral MPS orderings at D=64–128: retained norms in
  the `10^-25`–`10^-30` range; the apparent MAP strings are truncation
  artifacts.
* MPO at D=128 and cutoff `0.005`: completes 2,593/2,593 but samples are
  effectively flat.  D=512 at `0.002` completes under both ordinary and
  `flip_freq=2` routing, also flat.  At the P9-quality cutoff (`6e-4`) and at
  `1e-3`–`1.75e-3`, the router stalls far before completion.
* The overnight campaign added no solution: stage A reached 180/2,593 before
  the no-progress guard; pair-lookahead stages B/C reached only 24/2,593 and
  were wall/user stopped.
* Local-unitary and patch-fingerprint scans found strong short-window
  coincidences, but the inferred permutations are not stable over windows and
  do not establish a global unscrambling.

### New experiment

`scripts/peakfind.py` with the saved annealed ordering and a permutation-tracking
MPS (`D=128`, cutoff `1e-12`) completed all 10,486 parsed operations in 538 s:

* retained norm proxy: `1.6733e-20`;
* required fidelity gate: `100*2^-62 = 2.168e-17` — **failed**;
* top-1/top-2 ratio: `1.020x`, top-32 mean Hamming spread: `3.6`;
* verdict: **truncation artifact**, despite the enormous ratio to the uniform
  floor.

The completed loose-cutoff D128 extraction was also audited independently:
10,000/10,000 strings were unique, but the majority string was exactly the
supplied P6-A1 reference.  Its split-half majority differed by one bit and 61
of 62 bits were bootstrap-stable.  That is a stable *bias* of the loose
truncation, not evidence of a recovered answer; the run's own fidelity gate is
missing because its summary was left marked `running`.

### P6 decision

There is no verified P6 answer.  The useful uncompleted experiment is a proper
cutoff bisection around `1.5e-3`–`1.875e-3` with `flip_freq=2`, followed by an
adaptive cutoff-rescue controller.  It is not safe to spend another overnight
run on the old isolated interpreter.

## P8

### What has been tried

* Identity/spectral/permutation MPS, native graph PEPS/PEPO, TTN, graph-BP and
  TNO variants: either the state loses fidelity or the candidate family is
  unstable/underconstrained.
* The MPO controller has exercised bond, bond-profile, route-proxy,
  pair-lookahead, balance, cycle/tabu, tail-beam and absorption-frequency
  variants.  The older successful trajectory reached 804/808 but never reached
  sampling; no 808/808 run exists.

### New experiments

1. A P8 local-unitary scan (windows 8/16/32) gives large optimized-match z
   scores (`12`–`14`), but the q2 graph/mirror scan has permutation stability
   `0.0167` and a substantial mismatched-window control.  This is local
   structure, not a usable global mirror.
2. `scripts/peakfind.py` with annealed ordering, permutation MPS, `D=256`,
   cutoff `1e-14` completed in 217 s:

   * retained norm proxy: `7.3925e-19`;
   * required gate: `100*2^-40 = 9.095e-11` — **failed**;
   * top-1/top-2 ratio: `1.020x`, top-32 spread: `7.9`;
   * verdict: **truncation artifact**.

3. The new tail-materialization path was tested under the safe conda runtime.
   The clean `7296a2a` branch reached 781/808 with `flip2` and 782/808 with
   schedule `2->1` before intentional stops, so the eligibility condition
   (at most eight gates remaining) was not reached and no sample was produced.
   The older manifests that reached 804/808 are from the earlier `e1a6eef`
   checkout (marked dirty), and there is no checkpoint/resume file.  Thus the
   tail code itself remains unadjudicated on P8.

### P8 decision

There is no verified P8 answer.  The highest-value next run is to reproduce the
exact 804/808 `e1a6eef` trajectory in the safe conda environment, add the
tail-materialization code, and preserve the partial MPO.  This is a branch/
reproducibility task, not another generic bond or patience sweep.

## Result artifacts from this reassessment

* P6 annealed permutation-MPS: `results/new_p6_p8_20260831/p6_perm_annealed_D128.json`
* P8 annealed permutation-MPS: `results/new_p6_p8_20260831/p8_perm_annealed_D256.json`
* P6 extracted-sample audit: `results/new_p6_p8_20260831/p6_d128_extract_analysis/analysis.json`
* P6 loose D512 sample audit: `results/new_p6_p8_20260831/p6_d512_cut2e3_analysis/analysis.json`
* P8 unitary scan: `results/new_p8_structure_20260831/unitary/summary.json`
* P8 graph/mirror scan: `results/new_p8_structure_20260831/hqap/summary.json`
* Safe-runtime P8 tail attempts: `results/new_p8_tail_materialize_20260831_conda/` and
  `results/new_p8_tail_materialize_20260831_conda_schedule2to1/`
* Runtime smoke test: `results/new_runtime_preflight_20260831/`

The project test suite was rerun after the runtime fixes: **202 passed, one
non-fatal Quimb warning**.  The earlier process abort was specifically the
Matplotlib `macosx` backend; it no longer occurs.
