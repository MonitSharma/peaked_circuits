# Batch 001 instrumental-artifact screening

Checked: 2026-08-28

This is the free, target-blind screening requested before considering a decoy control. The reconstructed Batch 001 data and recorded provider metadata were inspected for the crudest attractor explanations.

## Findings

- The fixed collision string is Hamming distance **46** from all-zero and **52** from all-one. The 16 radius-31 cluster has mean distances **48.75** and **49.25**, respectively, compared with **50.25** and **47.75** over all 200 shots. The cluster is therefore not an obvious all-zero or all-one attractor.
- The archived backend metadata contains no per-qubit readout/gate-error snapshot and no final-layer gate record suitable for testing correlation with known-poor qubits or final single-qubit parameters.
- This screening cannot exclude correlated leakage, sticky detection states, compilation artifacts, or other machine-level attractors. A matched decoy remains the stronger control.

No candidate, hidden target, or tracker scoring was accessed. This document does not alter the frozen candidate, radius, or Batch 002 endpoints.
