# Next-experiment Codex prompt: P6 structural contraction screen

Copy the prompt below into Codex on a machine that has a genuine quantum Tsim
or equivalent ZX-contraction implementation.

---

You are continuing the P6 peaked-circuit investigation in:

`C:\Users\monitsharma\Downloads\SMU-Quantum\p12-helios-recovery`

Your objective is to test one genuinely new structural/contraction
representation for P6. Do not resume broad ordinary MPO cutoff, bond, ordering,
or routing sweeps unless a new structural result directly justifies one.

## Verified starting evidence

Read these before running anything:

- `docs/P6_REPOSITORY_AUDIT_20260901.md`
- `docs/P6_REPRESENTATION_INVESTIGATION_20260901.md`
- `results/p6_investigation_completion_matrix_20260901.json`
- `docs/PEAKED_FIDELITY_CALIBRATION.md`

The answer-blind P6 source is:

`results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm`

Its verified statistics are 62 qubits, 3,494 two-qubit gates, 6,992 U3
operations, 10,486 total operations, and depth 416.

Already-tested hypotheses are closed unless contradictory evidence appears:

1. direct PyZX reduction as an MPO rescue;
2. naive Clifford-plus-residual-Pauli/CAMPS construction;
3. split routing truncation under the tested controller;
4. scalar cutoff `1.875e-3` as a practical rescue;
5. the layer-207 permutation/reconstruction hypothesis.

## Safeguards

- Remain answer-blind. Do not read, print, embed, or compare against any
  target bitstring. Report only target-independent observables until a
  separately authorized validation step exists.
- Preserve all existing files and user changes. Never use destructive git
  commands or overwrite existing artifacts.
- Inspect the installed Tsim/ZX implementation and its license/API before
  running it. Do not confuse a package named `tsim` with a quantum simulator.
- Start with bounded controls and prefixes. Stop on explosive resource growth.
- Do not call a heuristic rank-width estimate a proven contraction bound.

## Phase 1: tool and representation audit

1. Record package versions, commit, hardware, Python version, RAM, and thread
   count.
2. Identify the exact circuit format accepted by the tool and write a small
   parser/converter test.
3. Validate the converter on a tiny hand-built circuit containing a Clifford
   gate, a non-Clifford rotation, and an entangling gate.
4. Confirm that gate order, qubit order, global phase convention, and measured
   versus unmeasured wires are handled explicitly.

## Phase 2: ZX/rank-width screen

Run the tool's rank-width or cut-rank heuristic on:

1. the original P6 diagram;
2. the exact `full_reduce` P6 diagram;
3. the exact `teleport_reduce` P6 diagram;
4. the corresponding P5 and P9 control diagrams if feasible.

For each result record:

- diagram vertex/edge count;
- decomposition strategy and seed;
- estimated rank width and contraction score;
- runtime and peak memory;
- whether the number is heuristic or a proven bound.

Use the values only as screening signals: roughly 15–20 may be interesting,
whereas above 35–40 is a warning, not a theorem.

## Phase 3: Tsim prefix screen

Run answer-blind prefixes containing approximately 100, 250, 500, and 1,000
two-qubit events for P5, P9, and P6 where resources allow. Use identical
precision and initialization conventions.

For every prefix record:

- events consumed and one-qubit operations included;
- wall time, peak resident memory, and thread count;
- stabilizer-term, decomposition, tensor, or sparse-term count exposed by the
  implementation;
- maximum intermediate rank/width;
- normalization or discarded-weight diagnostics;
- whether the run completed, stalled, or hit a resource limit.

Fit only a descriptive extrapolation. Do not extrapolate beyond the measured
regime if growth is superlinear or unstable. Stop P6 expansion if the resource
curve is clearly explosive.

## Phase 4: correctness and control gates

Before trusting any P6 result:

1. Validate the implementation exactly on small circuits using dense
   statevectors or full tensor comparison.
2. Run the same method on P5 and P9 controls.
3. Require the established control gates: P5 44/44 and P9 56/56, together
   with a non-flat peaked distribution and stable peak observables. Completion
   alone is not success.
4. Compare distributions, peak fraction, top-1/top-2 separation, and norm or
   overlap diagnostics. Keep the comparison answer-blind wherever possible.

If a control fails, stop the P6 full run and report the failure.

## Phase 5: bounded P6 test

Only if the controls pass and the prefix scaling is promising, run the smallest
P6 experiment that can distinguish the representation from ordinary MPO:

- use a fixed seed and record it;
- use a strict wall-time and memory budget;
- checkpoint before expensive contractions;
- record progress, intermediate width/rank, memory, normalization, and peak
  observables;
- stop on repeated no-progress or clearly explosive growth;
- do not silently change precision, cutoff, ordering, or basis mid-run.

Do not launch a full P6 end-to-end computation unless the bounded test shows a
material structural advantage and the controls remain valid.

## Required output

Write a new timestamped report and machine-readable JSON manifest containing:

1. environment and tool identity;
2. exact commands;
3. conversion and small-circuit validation;
4. rank-width/cut-rank measurements with heuristic labels;
5. Tsim prefix tables and scaling plots or tabular profiles;
6. P5/P9 control results;
7. P6 bounded-run telemetry;
8. explicit failures, timeouts, and resource limits;
9. a recommendation ranked by evidence, scientific value, compute cost,
   implementation risk, and probability of preserving the P6 peak.

End with explicit answers to:

- Did the new representation reduce the relevant contraction/routing width?
- Did it pass both positive controls?
- Is P6 scaling plausibly manageable?
- What single next experiment is justified?
- Which remaining hypotheses should be closed?

---
