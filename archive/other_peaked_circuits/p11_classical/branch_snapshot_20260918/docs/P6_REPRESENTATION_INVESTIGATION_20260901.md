# P6 representation investigation — 2026-09-01

## Scope

This is the first verified Phase-A result from the P6 representation campaign.
The corresponding Phase-0 repository audit is
`docs/P6_REPOSITORY_AUDIT_20260901.md`.
The source is the answer-blind circuit
`results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm`, whose
SHA256 is
`206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4`.

The source contains 62 qubits, 6,992 `u` gates, and 3,494 `cz` gates (10,486
operations, depth 416).

## PyZX workflow

The P6 launcher is `scripts/run_pyzx_p6.py`. It transpiles only to the exact
`rz/sx/x/cx` basis and records the source hash. No approximate angle snapping
or target information is used.

The initial launcher incorrectly passed the output of `teleport_reduce` to
`extract_circuit`. PyZX's documented implementation preserves a phase-master
graph that is not necessarily graph-like, so that call fails by design. The
launcher now uses `Circuit.from_graph(graph).split_phase_gates()` for the
teleport-preserving path. `full_reduce` continues to use `extract_circuit`.

Command used:

```powershell
\.venv-p6-pyzx\Scripts\python.exe scripts/run_pyzx_p6.py `
  --source results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm `
  --outdir results/p6_followup_pyzx_20260901 `
  --modes teleport_reduce
```

## Verified circuit metrics

| representation | operations | 2Q gates | CZ | CX | SWAP | depth |
|---|---:|---:|---:|---:|---:|---:|
| original | 10,486 | 3,494 | 3,494 | 0 | 0 | 416 |
| full_reduce extraction | 26,073 | 3,631 | 3,576 | 15 | 40 | 1,119 |
| teleport_reduce extraction | 98,280 | 3,494 | 0 | 3,494 | 0 | 3,611 |

Artifacts:

- `results/p5_p6_p8_recovery/P6/pyzx/p6_pyzx_full_reduce.qasm`
- `results/p6_followup_pyzx_20260901/p6_pyzx_teleport_reduce.qasm`
- `results/p6_followup_pyzx_20260901/pyzx_p6_results.json`

The answer-blind structural measurement command was:

```powershell
\.venv-p6-pyzx\Scripts\python.exe scripts/measure_pyzx_p6.py `
  --original results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm `
  --reduced results/p5_p6_p8_recovery/P6/pyzx/p6_pyzx_full_reduce.qasm `
  results/p6_followup_pyzx_20260901/p6_pyzx_teleport_reduce.qasm `
  --out results/p6_pyzx_structural_metrics_20260901.json
```

| representation | distinct interaction edges | natural-order cutwidth | mean/max span | raw work-gate proxy |
|---|---:|---:|---:|---:|
| original | 658 | 329 | 20.61 / 61 | 10,486 |
| full_reduce extraction | 710 | 380 | 21.39 / 61 | 26,073 |
| teleport_reduce extraction | 658 | 329 | 20.61 / 61 | 98,280 |

The cutwidth is for the source qubit order and is a transparent routing proxy,
not an optimized minimum-cutwidth or contraction bound. The raw work-gate
proxy is deliberately labelled as such: the extracted circuits use different
bases and are not the production solver's consolidated `u`/`cz` work-gate
format.

The PyZX rewrites are exact graph transformations, but an independent full
62-qubit statevector equivalence check is not feasible with the current local
resources. The output manifests record this as `exact_graph_rewrite`; future
MPO use must still validate observable/readout behavior on controls and on
short, directly checkable prefixes.

## Decision

Neither extracted representation is currently a promising direct MPO input:

- `full_reduce` increases the two-qubit count by 137 and increases depth by
  2.7x, with 40 extracted SWAPs.
- `teleport_reduce` preserves the two-qubit count but increases total gate
  count by 9.4x and depth by 8.7x.

Therefore no full P6 MPO rerun is justified from gate-count evidence alone.
The next high-value direction is the Clifford-plus-residual-Pauli feasibility
diagnostic, followed by the split absorption/routing cutoff experiment only
after P5/P9 calibration. The scalar cutoff question remains a separate,
unresolved closure experiment.

## Validation

The project environment reports:

```text
5 passed, 1 skipped
```

The skipped structural test lacks Qiskit in `.venv`; it is unrelated to the
PyZX launcher change. PyZX's own equality verifier was also attempted on the
full extracted circuit, but did not finish within a bounded observation
window; it was stopped without interpreting the timeout as a failure. The
primary equivalence evidence therefore remains the exact graph rewrite plus
exact-basis extraction, with no approximation or angle snapping.

## Clifford/residual-Pauli screen

The answer-blind diagnostic is `scripts/p6_clifford_diagnostic.py`. It keeps
the propagated Clifford frame in binary symplectic form and decomposes each
`u(theta, phi, lambda)` into chronological `RZ(lambda), RY(theta), RZ(phi)`
factors. Only angles within the explicit absolute tolerance of a `pi/2` grid
are classified as Clifford rotations.

Command:

```powershell
\.venv-p6-pyzx\Scripts\python.exe scripts/p6_clifford_diagnostic.py `
  --source results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm `
  --out results/p6_clifford_diagnostic_20260901.json
```

At tolerance `1e-8`, the diagnostic reports:

| quantity | value |
|---|---:|
| exact Clifford rotations | 6,661 |
| residual rotations | 14,315 |
| distinct propagated Pauli supports | 4,015 |
| binary support rank | 124 |
| nullity proxy (`residual_count - rank`) | 14,191 |
| profile points | 10,486 |
| median profile nullity proxy | 7,086 |
| maximum profile nullity proxy | 14,191 |
| maximum support weight | 37 of 62 qubits |
| mean support weight | 6.11 |
| consecutive merge opportunities | 174 |
| merged runs reaching a Clifford angle | 0 |

This is a negative feasibility screen for a naive CAMPS construction: the
residual set is large and globally linearly dependent, rather than a small
number of residual rotations with low support complexity. The reported
nullity is explicitly only a screening proxy; it is not the CAMPS/OFD theorem
and does not prove that every Clifford-augmented representation is
infeasible. It does, however, substantially weaken the original expectation
that the Clifford fraction alone would make P6 easy. The full per-event
profile is retained in `results/p6_clifford_diagnostic_20260901.json` for
plotting or further analysis.

## Split-cutoff P5 calibration

The ignored upstream solver checkout was patched to accept `--unswap-cutoff`.
The option is passed only to `unswap()`; physical absorption continues to use
`--cutoff`. A forced-routing smoke test exercised the unswap path on both P5
and P9 and completed without an exception.

The full answer-blind P5 calibration used:

```text
cutoff = 1.5e-3
unswap_cutoff = 2.0e-3
max_bond = 512
seed = 123
```

It completed all 902 consolidated work gates in 1,912 seconds. The endpoint
had peak fraction `0.003`, 995 unique samples out of 1,000, and a top-1/top-2
sample-count ratio of `1.5`. The established P5 control profile at the same
physical cutoff is a distinct mode with approximately 1.2% peak fraction and
approximately 7.8x top-1/top-2 separation. Therefore the split setting fails
the P5 fidelity regression, despite completing the circuit.

Decision: do not run P6 with this split setting and do not proceed to rescue
pulses. A P9 full calibration is unnecessary for the go/no-go decision because
the hard P5 control already failed. The result confirms the concern that
routing-only truncation is not physically neutral.

## Scalar cutoff closure run

The one requested P6 scalar experiment was launched with:

```text
cutoff = 1.875e-3
flip_freq = 2
max_bond = 512
abort_after_no_progress_unswap_cycles = -1
```

The live run reached only 94 of 2,593 consolidated work gates. It then
repeatedly returned to the same routing region; the log recorded a forced-drain
fizzle at `2332376 > 4 * 500000`, and the final `cycle_progress` row recorded
zero work gates consumed at unswap cycle 22. The final telemetry showed peak
bond 509, peak tensor size 2,279,700 elements, and retained-fidelity telemetry
of approximately 0.304.

The process was stopped only after this genuine no-progress condition, not
because of an ETA estimate. Since the solver was interrupted inside its
guard-disabled loop, its live `summary.json` remains labelled `running`; the
authoritative endpoint evidence is in:

- `results/p6_scalar_1p875e3_20260901/p6_c1p875e3_flip2/stats.json`
- `results/p6_scalar_1p875e3_20260901/p6_c1p875e3_flip2/run.log`

This run does not show completion below `2e-3`. It strengthens the conclusion
that the scalar cutoff transition is not a practical P6 rescue: `1.875e-3`
still stalls near the same early routing barrier, while `2e-3` completes only
with a flat, fidelity-destroyed readout.

## What the P5 method yielded when transferred to P6

The same production family was in fact tried: midpoint MPO compression with
SVD truncation, greedy unswapping, and SABRE-based routing. The controls show
that this method works on P5 and P9; the failure is P6-specific rather than a
failure of classical MPO in general.

| circuit / setting | consolidated work gates | result |
|---|---:|---|
| P5, cutoff `6e-4` | 902/902 | correct control; peak fraction about 0.012; top-1/top-2 about 7.8x |
| P5, cutoff `1.5e-3` | 902/902 | correct control; peak fraction about 0.012; top-1/top-2 about 6.3x |
| P6, cutoff `6e-4` | 86–148/2,593 | routing stall while preserving the useful tight-cutoff regime |
| P6, cutoff `1.0e-3` | 180/2,593 | routing stall |
| P6, cutoff `1.5e-3` | 89/2,593 | stopped for compute budget before a natural endpoint |
| P6, cutoff `1.75e-3` | 164/2,593 | stopped by operator while progress was decaying |
| P6, cutoff `1.875e-3`, `flip_freq=2` | 94/2,593 | genuine no-progress stall |
| P6, cutoff `2e-3` | 2,593/2,593 | completed, but flat readout; top-1/top-2 about 1.02–1.06x |
| P9, cutoff `1.5e-3` | 1,885/1,885 | correct control; peak fraction about 0.098; top-1/top-2 about 23.1x |

All-to-all hardware connectivity does not remove the simulator's linear MPO
ordering problem: non-neighboring interactions still require routing or
unswapping in the tensor ordering. Structurally, P6 has 62 qubits, 3,494
two-qubit events, depth 416, and 2,593 consolidated work gates, versus P5's 44
qubits, 1,892 two-qubit events, depth 173, and 902 work gates. Its measured
natural-order interaction cutwidth is 329 versus P5's 304, so the main gap is
not just a dramatic static cutwidth increase; P6 combines a longer, denser
trajectory with a much sharper fidelity-versus-routing tradeoff. P9 is an
important counterexample: at 56 qubits and 1,885 two-qubit events it passes the
same method, indicating that P6's circuit-specific interaction/phase structure
is the relevant distinction.

## Official-style TNO feasibility screen

The official upstream repository was fetched at commit `9a77ed8` and its
separate TNO method was adapted to the installed Quimb arboreal compressor.
The answer-blind runner is `scripts/run_tno_p5_p6_p9.py`; it supports explicit
two-qubit prefixes and records core bond/elapsed-time telemetry.

At `max_bond=16`, `cutoff=0.01`, `chunk_size=4`, and `local-late` compression,
the 100- and 250-event prefixes completed for all three circuits:

| prefix | P5 core result | P6 core result | P9 core result |
|---:|---|---|---|
| 100 | complete, bond 2–4, 0.75 s | complete, bond 4–8, 0.78 s | complete, bond 2–4, 0.94 s |
| 250 | complete, peak bond 13, 4.17 s | complete, peak bond 8, 1.75 s | complete, peak bond 4, 3.52 s |
| 500 | timeout at 125 s, bond 16 | timeout at 163 s, bond 16 | stopped after an uncheckpointed expensive compression |

The TNO screen therefore does not reveal an early P6-specific failure; P6 is
actually cheaper than P5 at the 250-event checkpoint. It does reveal that the
current CPU implementation reaches its bond-16 compression wall before a
500-event result can be established, including on the known controls. These
are representation-feasibility results only: no full TNO state/readout was
claimed, and no P6 target information was used.

## Secondary-tool availability

The local PyZX environment was checked for the remaining optional screens.
`pyzx` and Qiskit are available, but `tsim`, `stim`, and `networkx` are not;
the repository also contains no existing Tsim or ZX rank-width runner. The
only PyPI package named `tsim` (`0.1.0`) was inspected in an isolated install
and is an OCR string-similarity utility, not a quantum simulator; it was
removed afterward. PyZX
does contain a rank-width implementation, but the parsed diagrams have about
63,036 vertices (original), 29,988 vertices (`full_reduce` extraction), and
101,898 vertices (`teleport_reduce` extraction). The available greedy
decomposition is not a bounded screen at that size, so it was not launched as
an unbounded computation. No unsupported installation or unbounded secondary
simulation was started. These screens remain optional follow-up work, not
evidence for or against a P6 solution.

## Consolidated decision

The evidence now supports this practical ranking:

1. Exact PyZX reduction: rejected as a direct MPO route; both extracted forms
   are worse on two-qubit/depth/work metrics.
2. Naive Clifford-plus-residual-Pauli/CAMPS screen: low priority; the residual
   support set is large and reaches weight 37, with 14,315 residual rotations.
3. Split absorption/routing cutoff: rejected by the full P5 control; it
   completed but degraded the peaked readout.
4. Scalar `1.875e-3` cutoff: rejected as a practical rescue; P6 stalled at
   94/2,593 work gates.
5. Local adaptive unswap pulse: operational but not yet a solver. Verified
   answer-blind smoke tests show the controller fires on P5 (two pulse rows in
   a 30-gate run) and on P6 (one pulse at 23 gates in the bounded run), while
   P6 remained effectively stalled at 26/2,593 gates after more than three
   minutes. The attempted high-search full P5 calibration was stopped at
   182/902 gates after about 16 minutes because its routing configuration was
   too expensive; it was not counted as a correctness pass or failure.

The next serious research direction should therefore be a genuinely new
structural or contraction representation, such as a validated ZX/Tsim route
on a machine with those tools, or a new circuit invariant. The adaptive pulse
is worth retaining as an instrumented component for such a route, but the
current bounded evidence does not justify a full P6 run or claim of recovery.

## Explicit closure answers

1. **Best explanation for the P6 failure.** The current evidence supports a
   representation bottleneck at the interaction/routing boundary: tight
   physical truncation retains useful peak structure but cannot absorb the
   routed circuit, while loosening truncation admits routing at the cost of
   state fidelity. This is consistent with the P6/P5 controls and does not
   identify a single faulty layer.
2. **Did PyZX improve faithful routing progress?** No evidence supports that
   conclusion. `full_reduce` increased two-qubit work and natural-order
   cutwidth; `teleport_reduce` preserved the interaction structure while
   greatly increasing one-qubit/depth overhead. No faithful P6 MPO rerun was
   justified.
3. **Is CAMPS/OFD plausibly feasible?** The naive Clifford-plus-residual-Pauli
   construction is not a credible next implementation: 14,315 residual
   rotations, support weight up to 37, and zero merged runs reaching a
   Clifford angle are unfavorable. This is a screening result, not a theorem
   ruling out every CAMPS/OFD variant.
4. **Did split-cutoff routing preserve the controls?** No. The full P5
   calibration completed but lost the established peaked-readout profile.
   The later local adaptive unswap-pulse controller passed only operational
   smoke checks; its attempted high-search P5 calibration was stopped before
   completion, and the bounded P6 trial remained stalled. It is therefore not
   promoted as a P6 solution, and no P9 full same-controller correctness run is
   claimed.
5. **Is `1.875e-3` worth more investigation?** No, not as a scalar cutoff
   rescue. With `flip_freq=2`, it stalled at 94/2,593 work gates after a
   genuine no-progress condition.
6. **Single next experiment.** Run a bounded, answer-blind ZX/Tsim-style
   contraction screen on a machine with the required tooling, starting with
   P5/P9 controls and short P6 prefixes before any full P6 attempt.
7. **Hypotheses now closed.** Close the layer-207 reconstruction hypothesis,
   direct PyZX gate reduction as an MPO rescue, routing-only truncation under
   the tested split controller, and the scalar `1.875e-3` threshold. Keep open
   only genuinely new structural representations and independently validated
   contraction methods.
