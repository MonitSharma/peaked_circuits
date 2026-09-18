# P6 expert-review package

**Problem:** P6 / `P6_titan_pinnacle`  
**Prepared:** 2026-09-07  
**Repository branch:** `claude/p6-peak-recovery-92b9f7`  
**Purpose:** independent expert review of classical attempts, Helios-1 hardware results, optimized native-`ZZPhase` experiments, and emulator behavior.

## Executive summary

P6 is a 62-qubit circuit with a dense interaction structure. The original source contains 3,494 two-qubit CZ gates. Full statevector simulation is not practical on the MacBook: a 62-qubit complex state requires roughly 64 EiB before additional simulator overhead.

The original Helios-1 campaign produced 500 corrected shots across five 100-shot jobs. After correcting provider chunk assembly, all 500 strings were unique; there was no reproducible exact-string peak or stable full candidate. The five 100-shot jobs were charged 856.04 HQC each, approximately 4,280.20 HQC total.

An offline two-qubit optimization reduced the circuit to 2,798 native `ZZPhase` gates. The repository’s first QIR exporter incorrectly expanded those gates to 5,596 CZ gates, so a native-`ZZPhase` exporter was added. The native QIR passed Helios-1SC syntax validation and was run twice on Helios-1 for 50 shots each. Each optimized batch cost 453.42 HQC, returned 50 provider-reported shots, and contained 49 unique strings. The pooled 100-shot bitwise-majority candidate received the best post-generation verifier score observed so far: **54/62**.

This is substantial partial recovery, not an exact solution. The 54/62 score was obtained after candidate generation and submission; it is not an independent validation of the target-blind decoder. The emulator experiments do not rescue the situation: `chi=32` runs complete but produce diffuse, approximate distributions; `chi=64` runs fail with an end-of-stream error.

## 1. Circuit and artifact provenance

| Item | Value |
|---|---|
| Logical qubits | 62 |
| Original source | `artifacts/original_hardware/p6_helios_50shot_20260829/source.qasm` |
| Original QASM SHA-256 | `206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4` |
| Original two-qubit gates | 3,494 CZ |
| Optimized QASM | `artifacts/optimized_native_zzphase/p6_optimized.qasm` |
| Optimized native QIR | `artifacts/optimized_native_zzphase/p6_native_zzphase.qir.ll` / `.bc` |
| Native QIR SHA-256 | `0d68e1ad66e1619e30dfd2a8f7d9f22b7da1eec9dd4ae4815a09493425f56283` |
| Native bitcode SHA-256 | `494b1003132a910ca0a4f39bbb41f258561d4f7091f8d495fcd8f94e4f09c851` |
| Native gate counts | 29,536 Rz; 16,242 Rx; 2,798 ZZPhase; 62 measurements |

The optimization was performed offline with pytket peephole optimization and a native-ZZPhase rebase. It reduced the two-qubit gate count, but did not make the circuit classically easy: entanglement and interaction-graph complexity remain the limiting factors.

## 2. Classical work completed

The following families were attempted or reviewed:

1. **Low-bond MPS / tensor-network simulations.** MettleQ and permutation-MPS runs generated candidates but were diffuse or unstable. The reported classical MettleQ candidate scored 34/62 after evaluation.
2. **Higher-bond MPS.** Increasing bond dimension did not yield a stable, reproducible P6 peak.
3. **MPO and TNO-style truncation.** Tight settings stalled; looser settings completed without a trustworthy peak. A bounded TNO prefix reached only a small bond dimension before timing out.
4. **CircuitPermMPS / independent seeds.** Seed-dependent candidates disagreed and did not establish a stable answer.
5. **PEPS/PEPO marginal probes.** These produced marginals rather than full shots and were unstable; a PEPO numerical failure was recorded.
6. **Statevector feasibility.** Rejected on memory grounds for 62 qubits.
7. **Constrained candidate reconstruction and candidate-family ranking.** These produced hypotheses and overlap-constrained candidates, but aggregate overlap information cannot identify which individual bits are wrong.
8. **Target-blind hardware decoders.** Most frequent string, bitwise majority, weighted observed medoid, and cluster consensus were applied batch-by-batch and only pooled after independent analysis.

No classical method produced an exact, externally verified P6 answer before the hardware work.

## 3. Original Helios-1 hardware campaign: 500 shots

The original circuit/QIR was run in five independent 100-shot batches. Each batch used the same original bitcode SHA-256 `0109765b16777c76347857cf91860cd99f7ad6c42ae5a7a991399e484a16f155` and reported 856.04 HQC.

| Batch | Job ID | Shots | Reported HQC | Result handling |
|---:|---|---:|---:|---|
| 1 | `19c66922-84e0-4f78-99a7-5392f98a4143` | 100 | 856.04 | raw result plus framing audit |
| 2 | `c9156c8f-a385-4467-b388-fc58127e93b8` | 100 | 856.04 | raw result |
| 3 | `95960cce-a39d-4650-a0d7-f262e3b0d0b3` | 100 | 856.04 | raw result |
| 4 | `0da697e8-de3a-4034-a0b2-1c9ff350c7b5` | 100 | 856.04 | raw result |
| 5 | `35bab525-cea9-48ac-bdd0-9a3e067a2dea` | 100 | 856.04 | original chunks reconstructed independently |

**Total:** 500 corrected shots and approximately 4,280.20 HQC. After chunk-level correction, all 500 strings were unique. The repeated peaks seen in an earlier SDK assembly were artifacts of duplicated first-frame/chunk handling and were not retained.

The original campaign’s conclusion was `NO_REPRODUCIBLE_FULL_CANDIDATE`.

## 4. Native-`ZZPhase` Helios-1 hardware experiment

The native QIR passed Helios-1SC syntax checking:

- Syntax-check job: `06215946-2e5f-488b-8414-57b4fc4a7266`
- Target: `Helios-1SC`
- Status: completed
- No HQC or shots consumed

Two independent hardware batches were then submitted with the identical native bitcode:

| Batch | Job ID | Shots | Actual HQC | Unique strings |
|---:|---|---:|---:|---:|
| 1 | `e7261bb0-c9d6-4899-90ff-aa18070ae6bf` | 50 | 453.42 | 49 |
| 2 | `7decd713-d9df-47d7-b52a-62c411b581da` | 50 | 453.42 | 49 |

Combined cost was **906.84 HQC**. Each raw payload reconstructed one extra complete frame beyond the provider-reported 50 shots; the analysis used exactly the first 50 provider-reported frames and recorded the extra frame as excluded framing data.

The pooled 100-shot decoder candidate was:

`11101100100110000000100011010101111100001010000101100110100001`

It received a post-generation overlap of **54/62**, the best observed result. The first native batch’s bitwise-majority candidate scored 51/62. The native batches did not produce a repeated exact-string peak, and their batch-specific decoder outputs differed materially.

## 5. Helios-1E emulator experiments

All emulator work used the native QIR, 62 qubits, `NoErrorModel`, and MPS with `backend="auto"`. These were pipeline/diagnostic runs, not hardware evidence.

| Configuration | Job ID | Shots | Status | Actual HQC | Outcome |
|---|---|---:|---|---:|---|
| chi=128, threshold=.01 | `799101ba-5807-493e-86d0-eceb60107cc9` | 1 | cancelled | 0 | cancelled after prolonged run |
| chi=32, threshold=.05 | `34c1c442-b8a1-463c-9640-a9b8e5d9117e` | 1 | completed | 13.96 | successful one-shot probe |
| chi=32, threshold=.05 | `18423ac9-bf14-449c-a76a-130500be0b9d` | 100 | completed | 901.84 | 97 unique strings; one mode occurred 4 times |
| chi=64, threshold=.02 | `d217edb0-b227-4dd1-9f2d-84abc5be5b60` | 1 | error | 0 | `Unexpected end of stream` |
| chi=64, threshold=.05 | `54da889b-b860-4ed2-8443-879c79bf47b9` | 1 | error | 0 | `Unexpected end of stream` |
| chi=32, threshold=.05 | `b71f6f7a-2462-49a1-9bc6-7ebac434f0c9` | 1 | completed | 13.96 | repeat probe succeeded |

The 100-shot chi=32 emulator candidates scored only 28/62 (mode), 33/62 (bitwise majority), 34/62 (medoid), and 34/62 (cluster consensus). This demonstrates that “no physical error model” does not mean “near the correct answer”: MPS truncation remains a numerical approximation.

## 6. Candidate record and current interpretation

The full candidate list and supplied post-generation overlaps are in [`P6_CANDIDATE_LEDGER_20260907.md`](reference_docs/P6_CANDIDATE_LEDGER_20260907.md).

Current best: **54/62**, from the pooled native hardware batches. It is not an exact solution and should not be described as a solved P6 instance. The score is post-hoc verifier feedback, not an independent statistical validation.

The emulator candidates should not be submitted as replacements: they were generated by an approximate, noiseless MPS model and performed worse than the hardware-derived candidate.

## 7. Questions for an expert reviewer

1. Does the optimized native-ZZPhase QIR preserve the intended circuit semantics and measurement ordering?
2. Is the observed 54/62 partial recovery consistent with a noisy peaked distribution, a provider/runtime attractor, or a compilation artifact?
3. What target-blind decoder or tensor-network diagnostic could identify the remaining bits without using verifier overlaps?
4. Is there a principled circuit transformation that reduces entanglement/treewidth rather than only gate count?
5. Would a GPU tensor-network contraction, circuit cutting, or observable-only method be informative under a bounded computational budget?
6. What additional hardware control or decoy experiment would distinguish circuit signal from provider-specific behavior?

## 8. Package contents

- `artifacts/original_hardware/`: original 500-shot hardware outputs, chunk audits, corrected analyses, candidate reconciliation, GPU feasibility notes, and original QIR/source artifacts.
- `artifacts/original_emulator/`: prior P6 emulator submission records.
- `artifacts/optimized_native_zzphase/`: optimized QASM, native QIR/bitcode, syntax report, cost sweeps, both 50-shot hardware raw results, emulator raw results, and submission metadata.
- `reference_docs/`: supporting P6 reviews, cost plans, hardware reanalysis, protocol, and candidate ledger.

No hidden target was read during candidate generation. No quantum-advantage claim is made by this package.
