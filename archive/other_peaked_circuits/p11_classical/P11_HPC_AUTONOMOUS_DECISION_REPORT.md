# P11 HPC Autonomous Decision Report

Date: 2026-08-21 (+08:00)
Repository: /home/hclau/p11_classical/p12-helios-recovery
Branch: p11_classical
Campaign: results/p11_hpc/20260821_042737
Terminal state: NO_GO_HPC_ENVIRONMENT

## 1. Executive conclusion
Stop before P9-C, controlled scaling, and every P11 computation. Formal P9-A completed correctly, but formal P9-B completed normally at 36 threads and failed the known P9 calibration. The current HPC/profile/solver combination is therefore not numerically reproducible across the intended A/B profiles. Timing and P11 claims are unsupported. No P11 answer-bearing artifact, quantum output, emulator output, or public P11 bitstring was inspected or used.

## 2. Terminal state
NO_GO_HPC_ENVIRONMENT. This is a calibration/reproducibility stop, not a claim about the P11 answer.

## 3. Scope and blindness
P9 was used only as the known-answer control. P11 QASM and structural/resource data were allowed. All P11 commands in the repaired orchestrator pass an empty expected bitstring.

## 4. Experiment inventory
- Manual A: 18 physical cores; correct P9 calibration.
- Formal A: 18 threads, CPUs 0-17, memory node 0; correct P9 calibration.
- Formal B: 36 threads, CPUs 0-35, memory nodes 0,1; complete but P9 calibration failed.
- Formal C: not launched.
- P11: not launched.

## 5. P9-A validation
A is valid: 1885/1885 gates, normal completion, partial=false, valid 56-qubit permutation, 1000 samples, correct known P9 modal prediction, and complete artifacts. Compression 7760.35 s; sampling 29.53 s; peak bond 512; peak total elements 1,136,932; modal count 23/1000.

## 6. P9-B validation
B is structurally complete but scientifically invalid: 1885/1885 gates, normal completion, partial=false, valid permutation, 1000 structurally valid 56-bit samples, stats JSON/CSV agreement, no temporary stats file, compression 11670.74 s, sampling 29.53 s, peak bond 512, peak elements 1,021,216, modal count 98/1000, and known P9 modal mismatch. This is a clean numerical failure, not truncated output.

## 7. Manual/formal comparison
| Metric | Manual A | Formal A | Formal B |
|---|---:|---:|---:|
| Threads/profile | 18 | 18/one node | 36/two nodes |
| Compression s | 2088.45 | 7760.35 | 11670.74 |
| Sampling s | 30.60 | 29.53 | 29.53 |
| Peak bond | 512 | 512 | 512 |
| Peak elements | 1,136,932 | 1,136,932 | 1,021,216 |
| Modal count | 23/1000 | 23/1000 | 98/1000 |
| P9 control | correct | correct | failed |

## 8. Trajectory comparison
The first cycle-level difference is cycle 32: both runs consumed 328/1885 gates and had max bond 8, but A had 692 elements/394 shapes while B had 788/410. Representative times (A/B seconds): 87 gates 1085/1317; 199 gates 1715/2690; 304 gates 2758/4980; 492 gates 3134/6575; 700 gates 3509/8152; 997 gates 4438/9726; 1393 gates 6693/10679; 1835 gates 7615/11496.

## 9. CPU, affinity, NUMA
A used one_node, 18 threads, CPUs 0-17, memory node 0. B used two_nodes, 36 threads, CPUs 0-35, memory nodes 0,1. B had 107 total threads, OpenBLAS/NumPy 36 threads, about 1.25 GB RSS in observation, pages mainly on nodes 0,1, and machine load around 40+. Runs were not isolated or randomized.

## 10. Environment/provenance
Both used the same observed dirty solver checkout: commit 3bcdc1e5bfd6abb9425f71bd43e560d2b27f45c1, with modified solver files and untracked compatibility/patch files. NumPy 2.2.6, SciPy 1.15.3, Qiskit 1.4.5, Quimb 1.11.2, Python 3.10.21, OpenBLAS 0.3.29 for NumPy and 0.3.28 for SciPy. Dirty provenance is a major limitation; threading alone is not proven causal.

## 11. Runtime phase decomposition
| Phase | A s | B s |
|---|---:|---:|
| Initial rewire | 3.65 | 3.24 |
| Absorb probes | 4019.71 | 5252.99 |
| Unswap | 3265.17 | 5793.74 |
| Rewire total | 249.02 | 350.04 |
| Compression total | 7760.35 | 11670.74 |

## 12. Runtime diagnosis
Supported: formal A is about 3.72x slower than manual A; B is slower than formal A despite twice the threads; sampling is unchanged; B has much larger unswap and probe costs; contention and dirty provenance were present. Likely contributors are NUMA traffic, contention/frequency variation, threaded BLAS reduction behavior, and source/config differences. No single cause is established.

## 13. Numerical reproducibility
B diverges in tensor trajectory before sampling and fails the known P9 control. Possible causes include threaded reduction order, truncation decisions, or dirty source/environment differences. This cannot be treated as performance-only behavior.

## 14. H0 audit
H0 passes for A and fails for B as an independent confirmation. The campaign cannot advance.

## 15. H1 audit
The old orchestrator accepted high-bond file completion. It now requires a D512 comparator, D1024/D2048/D4096 at a fixed 250-gate horizon, complete stats, and preregistered quantitative capacity and saturation-improvement thresholds. H1 was not exercised.

## 16. H2 audit
The old wording overclaimed routing evidence. It now records only a real P9 MPO-integrated pair-lookahead calibration and explicitly makes no beam-vs-greedy claim. H2 was not exercised.

## 17. H3 audit
The old H3 accepted executed files. It now requires a 350-gate bounded P11 horizon, non-partial output, valid stats and launcher artifacts, RSS below the configured limit, an explicit M3 failure baseline, and progress beyond that baseline. H3 was not exercised.

## 18. H4 audit
The old code could claim P11 success after stages executed. H4 is now unreachable until H1-H3 pass and longer stages have exact, complete, empty-expected-bitstring artifacts. H4 was not exercised.

## 19. Infrastructure changes
Applied on p11_classical: strict P9 validation; strict P9 manifest validation; strict P11 summary/stats/launcher/empty-expected validation; stale-resume and RUNNING-stage guards; quantitative H1/H3 gates; fail-closed H4 sequencing; added P9 provenance fields. The numerical method was not changed for timing.

## 20. Tests
Python compilation passed. tests/test_hpc_preparation.py passed: 3 tests. B structural checks passed for permutation, sample count and widths, stats agreement, no temporary stats, and manifest presence. The B P9 calibration assertion correctly fails.

## 21. Provenance hashes
B summary.json ad02267e850bf3dd0d142e7b08ed94d2aaa6137c48c7402f24ad2843861b9dc3; stats.json b4a33a5e8e17981d5a38f12b6605084636d5190b4bc39ff00ae9977e189ee4ed; stats.csv 7d1960273dbd2b20d1620ef71bbf4308ecbe7c404e75c551949cc4597e2f8796; samples.tsv 16c997cc1227239c79738f9a15528944c97a85f52fb505b7909744b695ca22c7; p9_B.p9_manifest.json 1cc05d031b83e3198dfda42cce33897c8f8056f308a2366e8b84c863b1208e9c.

## 22. Failed hypotheses and uncertainties
Unsupported: more physical cores automatically improve time; a complete 36-thread run confirms calibration; A/B timing scales scientifically without control; clean exit implies numerical validity. Remaining uncertainties are clean-checkout effects, fixed-thread reproducibility, BLAS determinism, NUMA isolation, contention, and method stability.

## 23. Recommended next action/resource envelope
Do not launch P9-C, scaling, or P11 under current authorization. Any future computation requires human approval and a preregistered protocol: clean and hash solver; fix patches; repeat fixed-profile P9 controls; require identical calibration; then run serialized A/B/C P9 scaling with affinity, NUMA, load, RSS, BLAS threads, and phase metrics. No P11 resource envelope or exact parameters are recommended from this failed calibration.

## 24. Supported/unsupported claims
Supported: A reproduces P9; B completes structurally but fails P9; A/B trajectories diverge before sampling; current multi-profile HPC is not reproducible; the orchestrator now fails closed. Unsupported: P11 success or bitstring claims, beam-beats-greedy claims, scientific A/B/C scaling claims, and P11 readiness.

## 25. Final decision
NO_GO_HPC_ENVIRONMENT. Stop the campaign, preserve all result directories and provenance, and require a human decision before new HPC computation.
