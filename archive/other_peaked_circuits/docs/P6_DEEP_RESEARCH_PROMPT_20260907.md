# Deep-research prompt: P6 quantum/hybrid recovery review

Please perform an independent, technically critical review of the complete P6 investigation in the repository below:

- Repository: https://github.com/MonitSharma/p12-helios-recovery
- Branch: `p12_quantum`
- Review commit: `2a97870` (`Add complete P6 hardware emulator analysis package`)
- Main package: [`results/p6_expert_review_20260907/`](https://github.com/MonitSharma/p12-helios-recovery/tree/p12_quantum/results/p6_expert_review_20260907)
- Main report: [`results/p6_expert_review_20260907/README.md`](https://github.com/MonitSharma/p12-helios-recovery/blob/p12_quantum/results/p6_expert_review_20260907/README.md)
- Candidate ledger: [`docs/P6_CANDIDATE_LEDGER_20260907.md`](https://github.com/MonitSharma/p12-helios-recovery/blob/p12_quantum/docs/P6_CANDIDATE_LEDGER_20260907.md)

Treat the repository contents as the primary evidence. Do not infer an exact hidden answer from post-generation overlap scores, and do not treat the P11/P12 successes as proof that P6 must have the same behavior.

## Problem and objective

P6 is a 62-qubit hidden-bitstring circuit. The objective was to determine whether classical simulation, Quantinuum Helios hardware, or Helios-1E MPS emulation could produce a reproducible output peak or a defensible candidate. The investigation also tested whether a two-qubit/native-gate optimization improved the signal or merely changed the implementation.

## Work completed

Review all of the following, including raw results rather than only summaries:

1. Classical approaches: low-bond MPS, higher-bond extrapolation, constrained/structured analyses, tensor/path feasibility checks, candidate clustering, bitwise/medoid/consensus decoders, and stability tests.
2. Original Helios-1 hardware campaign: five 100-shot batches, raw result framing, chunk reconstruction, frequency analyses, pooled analyses, and candidate reconciliation.
3. Optimized native-ZZPhase route: reduced circuit representation, compile metadata, Helios-1SC syntax validation, native QIR/bitcode, cost estimates, and two 50-shot hardware batches.
4. Helios-1E emulator attempts: chi=32 probes and 100-shot run, chi=64 failures, chi=128 cancellation, and the associated Selene errors.
5. Positive controls and independent audits: framing checks, corrected shot assembly, candidate-ledger comparisons, and GPU/statevector feasibility analysis.

## Key facts to verify

- P6 has 62 qubits and originally 3,494 CZ gates.
- A full statevector is infeasible on the available Mac memory; the report estimates roughly 64 EiB for the raw statevector.
- The original 500 hardware shots were split into five 100-shot jobs. After corrected reconstruction, the outputs were effectively diffuse, with no reproducible exact peak.
- Native optimization reduced the circuit to 2,798 native `ZZPhase` gates plus one-qubit rotations and measurements. Confirm whether this is a genuine physical simplification, a representation change, or both.
- The native route passed Helios-1SC syntax validation and cost approximately 453.42 HQC per 50-shot batch.
- The two optimized hardware batches produced a pooled 100-shot bitwise-majority candidate with a post-generation verifier overlap of 54/62. This is the best observed overlap, but it is not an unbiased validation statistic because the hidden target was used after generation to score candidates.
- The chi=32 Helios-1E 100-shot run produced a diffuse output distribution. Its recorded decoder candidates scored approximately 28/62 for the mode and 33–34/62 for majority/medoid/cluster decoders.
- chi=64 emulator attempts failed with `Parsing error: Unexpected end of stream`; chi=128 was cancelled. Explain what these failures do and do not establish about emulator accuracy.

## Questions to answer

1. Is the 54/62 hardware candidate evidence of a real P6 signal, a decoder artifact, or insufficient to distinguish the two?
2. How should the five original hardware batches and two optimized batches be pooled, if at all?
3. Does the native-ZZPhase optimization preserve the intended circuit semantics? Check gate conventions, QIR export, measurement order, bit order, and any provider-specific framing assumptions.
4. Are the raw hardware results and reconstructed shots sufficient for an independently reproducible analysis?
5. What statistical tests remain valid without using the hidden target during candidate selection?
6. How should the post-generation overlap scores be reported without overstating them?
7. What can be inferred from the chi=32 emulator result, and what cannot be inferred because chi=64 failed before producing samples?
8. Are there feasible classical methods still worth trying on a Mac CPU, or has the available evidence justified stopping classical simulation?
9. Would a GPU, tensor-network, stabilizer decomposition, circuit cutting, operator backpropagation, or higher-bond MPS plausibly change the conclusion? Give resource estimates and identify assumptions.
10. Is another Helios hardware run scientifically justified? If yes, specify the smallest informative protocol, pre-registered decoder, stopping rule, and required metadata. If no, explain why additional shots are unlikely to resolve the ambiguity.
11. What would count as an independently verifiable solution rather than merely a high-overlap candidate?
12. Separate all claims about recurrence, candidate recovery, circuit behavior, and quantum advantage. In particular, do not claim quantum advantage from a hidden-answer overlap or from hardware execution alone.

## Required output

Produce:

- an evidence table mapping each claim to the exact repository artifact supporting it;
- a reconstruction of the best candidate-generation pipeline without using the hidden target;
- a validity audit of the hardware and emulator analyses;
- a ranked list of remaining experiments, with expected information gain and cost;
- a clear conclusion: solved, unresolved but promising, or unsupported;
- explicit corrections to any overclaiming, invalid statistics, or reproducibility gaps.

Use the repository state at commit `2a97870` as the review baseline and identify any result that cannot be reproduced from the committed files alone.
