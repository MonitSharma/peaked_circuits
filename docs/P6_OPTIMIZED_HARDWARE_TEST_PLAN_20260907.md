# P6 optimized-circuit test plan

Status: offline preparation only. No hardware job is authorized by this
document.

## Rationale

The five corrected P6 Helios batches produced no reproducible exact-string
peak. Offline analysis indicates that the submitted QIR was a plain rebase and
that the two-qubit workload can be reduced before another physical test. The
optimization is therefore a new experiment, not an extension of the previous
unoptimized 500-shot pool.

## Compilation artifact

Run from this worktree with the repository's validated Python environment:

```text
PYTHONPATH=src .venv/bin/python tools/prepare_p6_optimized_compile.py
```

The script performs no provider calls. It applies:

1. `FullPeepholeOptimise(allow_swaps=False, target_2qb_gate=TK2)`;
2. `NormaliseTK2`;
3. `DecomposeTK2` using a documented offline ZZPhase fidelity proxy.

The generated QASM and metadata are stored under
`results/hardware/p6_optimized_compile_20260907/`. The fidelity proxy is only
for selecting a decomposition offline; it is not Quantinuum calibration data.

The first local run reduced the source from 3,494 CZ gates to 2,798 native
ZZPhase gates. However, the current repository QIR path does not preserve
ZZPhase: rebasing to the provider-compatible `{Rz,Rx,Ry,CZ,X}` set expands the
artifact to **5,596 CZ gates**. Therefore the 2,798-ZZPhase result is not yet a
hardware-ready improvement.

## Cost check (2026-09-07)

The installed Nexus cost-confidence API accepts `Helios-1`, not
`Helios-1SC`. Helios-1SC is a syntax-check target and does not provide a
shot-scaled execution-cost ladder. The provider-supported cost-confidence
request therefore used the provider-compatible QIR and the `Helios-1` costing
endpoint; no emulator or hardware execution was submitted.

| Shots | Estimated HQC | Confidence |
|---:|---:|---:|
| 1 | 22 | 95% |
| 5 | 90 | 95% |
| 10 | 174 | 95% |
| 20 | 342 | 95% |
| 50 | 846 | 95% |
| 100 | 1,686 | 95% |
| 150 | 2,526 | 95% |
| 200 | 3,366 | 95% |
| 300 | 5,046 | 95% |
| 400 | 6,727 | 95% |

The cost report and provider-compatible QIR are retained under
`results/hardware/p6_optimized_compile_20260907/`. These numbers mean the
current optimized artifact should **not** be submitted: at 200 shots it is
estimated at 3,366 HQC, roughly twice the original P6 estimate. A viable
optimized experiment requires either a provider-supported native ZZPhase/RZZ
QIR path or a different decomposition whose actual provider gate count is
lower, followed by a new syntax and cost check.

## Pre-registered pilot

Before any submission:

- obtain a fresh provider-supported cost estimate for exactly 200 shots;
- verify the optimized QASM, output width, measurement mapping, and submitted
  artifact hash;
- compare the cost against an explicit HQC ceiling;
- freeze the decoder and acceptance rule below.

For the pilot, use exactly 200 shots on the optimized circuit. The primary
structural endpoint is the number of shots within Hamming distance 18 of the
frozen P6 centre produced by the offline light-cone decoder. Exact recurrence
is a secondary endpoint because the prior unoptimized circuit produced no
exact repeats.

Do not promote a candidate from the pilot unless all of the following hold:

- the centre is stable under independent decoder initializations;
- the split-half centre distance is at most 4 bits;
- bootstrap median distance to the full-data centre is at most 4 bits;
- the primary cluster-mass statistic exceeds its frozen uniform-null
  threshold;
- the candidate is generated without using external overlap scores.

If these conditions fail, stop. Do not pool the pilot with the old
unoptimized shots and do not submit another batch automatically.

## Boundary

This plan is a preparation and decision document. No hardware submission,
HQC spend, hidden-target lookup, or external candidate scoring is authorized
by it.
