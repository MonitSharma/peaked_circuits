# P11 classical peak recovery: low-bond distillation plan

This branch (`research/p11-distillation`) implements the low-bond MPS
distillation experiment defined by the attached research brief. The scientific
target is one-bit marginal sign recovery, not global wavefunction fidelity.

## Guardrails

- P11 remains blind. No tracker submission, leaked bitstring, hidden oracle,
  quantum-hardware result, or emulator result may be read or used.
- P9 is the only calibration control and must be evaluated before P11.
- The fixed gates and run limits in the research brief are binding. No open-
  ended cutoff, bond, routing, or decoder sweep is allowed.
- Historical `results/p11_diagnosis` and `results/p11_research` artifacts are
  preserved and are not overwritten.
- A blind candidate is written only after `FINAL_P11_BLIND_CANDIDATE.json`
  has been produced and checksummed, before any external comparison.

## Stages

1. Audit and reproducibility freeze: repository, environment, input hashes,
   tests, machine, and historical-result inventory.
2. Implement a clean, checkpointable MPS engine with direct and sample
   marginal estimators, logical permutation restoration, RSS telemetry, and
   deterministic seeds.
3. P9 blind-style fixed ladder: `D = 16, 32, 64, 128, 256`; at most one
   diagnostic at `D=512` if Gate A fails.
4. P9 robustness: at most three routing seeds by two adjacent useful bond
   values. Apply Gates A and B and freeze the protocol if both pass.
5. Run the frozen protocol on P11 only. Apply Gate C before any conditional
   decoding, and Gate D before candidate freeze.
6. Use the authorized marginal-only tensor-network fallback only if P11 has
   already demonstrated meaningful marginal signal and only within its three
   variant limit.

## Current audit status

The repository contains historical P9/P11 diagnostics but not the canonical
P9/P11 QASM files or the external MettleQ checkout. Historical manifests record
the P9 input hash as `cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35`
and the P11 input hash as
`1373d50c8a42b1ca745d202391767c417ddac56db95182ac2aced019231b3372`.
These hashes are provenance only; no P11 output or answer is used. Execution
must remain blocked until the exact input QASMs and a compatible engine are
available locally.

The tracked P12 QASM is not a substitute for either calibration input. Its
hash is recorded in `results/p11_distillation/AUDIT.json` for completeness.

## Required evidence

The run directory must contain the fixed-ladder tables, marginal and stability
tables, frozen protocol (if Gates A/B pass), blind P11 tables (if P11 starts),
plots, reports, and SHA256 manifests specified in the research brief. Missing
inputs or a failed gate produces a documented no-go result rather than an
unjustified candidate.
