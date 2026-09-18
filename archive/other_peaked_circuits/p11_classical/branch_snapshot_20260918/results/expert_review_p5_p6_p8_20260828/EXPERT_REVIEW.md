# Expert review package: P5, P6, and P8

Date assembled: 2026-08-28  
Repository workspace: `p12-helios-recovery`  
Purpose: provide an auditable record of the classical simulation and candidate-extraction work performed on P5, P6, and P8.

## Executive summary

There is currently **no externally validated answer** for P5, P6, or P8 in this package.

P5 and P6 have MPS/distillation candidates with supporting bootstrap and per-bit marginal data. P8 has several independent exploratory candidates, but they do not agree. The P8 PEPS ladder is unstable, the PEPO implementation produced an invalid probability on its first bounded probe, and no valid independent P8 TNO result is present.

These results are suitable for expert review and method selection. They are not, by themselves, submission-grade proofs of the hidden bitstrings.

## Input circuits

The exact input QASM files copied into `inputs/` are:

| Problem | File | Description from local filename |
|---|---|---|
| P5 | `P5_granite_summit.qasm` | 44-qubit peaked circuit |
| P6 | `P6_titan_pinnacle.qasm` | 62-qubit peaked circuit |
| P8 | `P8_grid_888_iswap.qasm` | 40-qubit grid/iSWAP circuit |

The input files are copied from `<local-user>/Downloads/` and their hashes are recorded in `MANIFEST.json` and `SHA256SUMS`.

## Results by problem

### P5

Method run: low-bond MPS marginal distillation, D=64, cutoff `1e-2`, 1,000 samples.

- Candidate length: 44 bits.
- Candidate: `00010110000100100101100011011101110010110011`
- All 1,000 sampled strings were unique; modal frequency was 1.
- Split-half Hamming disagreement: 5 bits.
- 39/44 bits passed the local bootstrap threshold of 0.90.
- This is a weak-to-moderate candidate, not an independently verified answer.

Evidence is in `results/distillation/`, `results/mettleq/p5_D64_c1e2_seed123/`, and the additional D=128 P5 run in `results/mettleq/p5_D128_c5e4_seed456/`.

### P6

Method run: low-bond MPS marginal distillation, D=64, cutoff `1e-2`, 1,000 samples.

- Candidate length: 62 bits.
- Candidate: `11011011110101011010100010111011001100010100000011100001110010`
- All 1,000 sampled strings were unique; modal frequency was 1.
- Split-half Hamming disagreement: 0 bits.
- 62/62 bits passed the local bootstrap threshold of 0.90.
- This is the strongest local candidate of the three, but it still lacks independent solver agreement or external verification.

Evidence is in `results/distillation/` and `results/mettleq/p6_D64_c1e2_seed123/`.

### P8

P8 was tested with several distinct approximate approaches.

#### MettleQ MPS distillation

- D=64, cutoff `1e-2`, 1,000 samples.
- Candidate: `0010111110100001101010111000001111111011`.
- 1,000 unique samples; modal frequency 1.
- Local split-half check: 0 disagreements; 38/40 bits above the 0.90 bootstrap threshold.

#### CircuitPermMPS distillation

Two D=128, cutoff `1e-12`, 1,000-sample runs were performed with seeds 123 and 456. Their voted candidates differ, and both have zero observed modal frequency. The artifacts explicitly classify the signal as weak unless repeated.

#### PEPS simple update

The runner constructs the unique interaction graph from the Qiskit circuit and uses complex128 tensors. The current runner uses the explicit 4x4 iSWAP matrix recorded in the script metadata.

Completed protocol points:

| Bond | Cutoff | Cluster distance | Status | Candidate / observation |
|---:|---:|---:|---|---|
| 4 | `1e-10` | 2 | completed | `0111000101000100010010011111101100111001` |
| 4 | `1e-10` | 3 | completed | `0111001101001110010010011111101100110001` |
| 8 | `1e-10` | 2 | completed | `1011111001011110100000001000011110001001` |
| 8 | `1e-2` | 1 | prior exploratory run | unstable margins |
| 16 | `1e-3` | 1 | prior exploratory run | unstable margins |

D=12 at distance 2 exceeded the 120-second bounded run. Distance-4 all-site evaluation became memory- and time-intensive and was stopped. The completed PEPS candidates do not stabilize across bond and cluster settings.

#### PEPO simple update

The PEPO runner was patched to use the same explicit iSWAP matrix. A bounded D=8, cutoff `1e-3` site-0 probe returned `p0=-1.03e-4`, which is physically invalid. It is retained as a numerical-failure artifact, not as evidence for bit 0.

#### TNO and exact contraction

No valid independent P8 TNO result is included. Exact sliced amplitude scoring was not run because the prior estimate was approximately `1.8e16` complex-element scale before slicing, making it unsuitable for the available CPU budget without a substantially better contraction strategy.

## Method status matrix

| Method | P5 | P6 | P8 | Interpretation |
|---|---|---|---|---|
| MettleQ low-bond MPS distillation | run | run | run | candidates only; no external validation |
| CircuitPermMPS distillation | not included | not included | run, two seeds | P8 candidates disagree |
| PEPS simple update | not run | not run | partial ladder | unstable and expensive |
| PEPO simple update | not run | not run | bounded site-0 probe | numerical failure |
| Valid independent TNO | not run | not run | not completed | open |
| Exact sliced amplitude | not run | not run | not run | estimated too expensive |
| Sparse tensor network | not run | not run | not run | correctly deferred |

## Bit ordering and provenance limitations

The artifacts record Qiskit logical order, internal MPS permutations where available, and simple reversed strings. A single verified P3 `logical_to_portal()` round-trip function was **not** established in this package. Therefore candidate strings must not be submitted until the expert or Tracker procedure confirms the required portal ordering.

The P8 runners record both `bitstring_q0_first` and `reversed`, but reversal alone is not evidence that either string is in the external portal’s expected order.

## What an expert should review

1. Whether the P5/P6 distillation candidates meet the relevant Tracker submission criteria despite unique samples.
2. Whether the P8 PEPS approximation is mathematically appropriate for the iSWAP graph and whether cluster-radius evaluation is being interpreted correctly.
3. Whether the PEPO normalization and reverse-lightcone contraction should be redesigned before further P8 runs.
4. Whether the P8 QASM gate semantics and logical-to-portal bit ordering are independently verified.
5. Whether an official TNO, tensor-network, or exact-slicing implementation is worth pursuing.

## Package contents
- `inputs/`: source QASM files.
- `results/distillation/`: candidate summaries and per-bit bootstrap analyses.
- `results/mettleq/`: raw samples, logs, CSV telemetry, JSON telemetry, and summaries.
- `results/peps/`: prior and newly run P8 PEPS outputs.
- `results/pepo/`: P8 PEPO bounded numerical-failure output.
- `results/circuitpermmps/`: independent P8 CircuitPermMPS outputs.
- `results/nexus/`: existing P8 QIR/dry-run artifacts; no hardware result.
- `scripts/`: runners and analysis scripts used for the included results.
- `MANIFEST.json`: machine-readable artifact inventory and status notes.
- `SHA256SUMS`: checksums for every package file.

No hardware or emulator measurement result is included. The package contains no hidden target, external verifier output, or claimed P5/P6/P8 answer.
