# Batch 002 Helios-1 confirmation plan

Status: prepared, not submitted.

## Purpose

Batch 002 is an independent confirmation of the pre-registered Batch 001 collision/cluster hypothesis. It must be analyzed independently before any pooling or decision about a third batch.

## Frozen inputs

- Branch: `p12_quantum`
- Circuit: `peaked_circuit_P12_Hqap_98x2457`
- Target: physical `Helios-1`
- Requested shots: exactly `200`
- Batch role: `confirmation`
- Batch 001 candidate freeze hash: `7b0c741082ffc3cfa1702fc3d9574892b1f8173f7381c149eee66a6c7b5c7403`
- Batch 001 collision hypothesis: `hardware_campaign/batch_001/collision_hypothesis.json`
- Protocol hash: `d88ea05069834adad820c75046022a678cda2a43ba9944ebf6793133a41898c5`
- Frozen QIR bitcode SHA-256: `c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`
- Planning estimate: `1374 HQC`, confidence `95%`
- Hard maximum cost: `1500 HQC`

The current estimate is the previously recorded provider estimate for this frozen QIR. A fresh provider estimate should be attempted during final preflight; if the endpoint is unavailable, retain this fallback explicitly rather than silently changing the cap.

## Submission boundary

This document prepares Batch 002 only. It does not authorize submission. Before execution, require a final exact-target preflight, current credit check, explicit user authorization, and a deterministic neutral provider job name. There must be no active Batch 001 job and no duplicate Batch 002 submission.

## Required evidence

Preserve the project reference, QIR artifact reference, job ID, result reference, target/backend metadata, submitted QIR bytes, raw provider payload, provider status history, queue/running/completion timestamps, reported cost, all input hashes, package versions, and SHA-256 checksums.

If the provider repeats the Batch 001 framing behavior, preserve the raw payload unchanged and apply only a predeclared structural reconstruction rule. Never select records based on which result resembles the frozen candidate.

## Batch 002 analysis order

1. Retrieve and preserve the raw result.
2. Validate shot framing and reconstruct only under the predeclared structural rule.
3. Analyze Batch 002 independently; do not pool first.
4. Use the two co-primary endpoints: (a) exact-match count of the fixed Batch 001 collision string, and (b) count of Batch 002 shots within Hamming radius 31 of that same fixed string.
5. Use secondary endpoints: descriptive pair counts at radii 0, 1, 20, and 30; cluster-restricted majority; split-half stability; random-subsample Hamming distributions; and provider-order blocks. Pair counts must not receive Poisson p-values because the pair events are dependent.
6. Compute per-bit diagnostics and exact-binomial tests with BH/FDR and Holm corrections as descriptive secondary analyses, not as post-hoc anchor selection.
7. Compare Batch 002 with the frozen Batch 001 collision hypothesis and record exact-match count, cluster overlap, and candidate Hamming distances.
8. Only after independent analysis, compute the pooled 400-shot diagnostics.
9. Decide whether Batch 003 is warranted using the predeclared rules below.

## Pre-registered thresholds and decision rules

- Do not use hidden-target scoring, external oracle feedback, or adaptive candidate selection.
- Exact-match count **at least 1** is strong recurrence evidence under the simple uniform null.
- Fixed-centre radius-31 cluster mass **at least 5** is strong directional reproduction; mass **1–4** is weak/directional; mass **0** is no cluster reproduction.
- Treat the two endpoints as co-primary. One endpoint positive and the other negative is mixed evidence and must be reported as such, not converted into a success by selecting a different candidate or radius.
- Both endpoints at zero provide no support for recurrence and close the current hypothesis unless a separately documented data-quality failure is found.
- Favor stopping after Batch 002 if both co-primary endpoints reproduce, stability improves materially, and the predeclared secondary endpoints agree. Consider Batch 003 only for a directionally consistent but inconclusive result.
- Do not call either batch a validated answer based on recurrence alone, and do not equate recurrence statistics with a quantum-advantage claim.

The radius-31 choice was made after inspecting the Batch 001 distance distribution. It is frozen for Batch 002, and the cluster endpoint is deliberately defined around the fixed pre-registered Batch 001 string. Selecting a new Batch 002 cluster would reintroduce a look-elsewhere degree of freedom.

The nominal uniform-null probability of at least one exact match in 200 fresh 98-bit shots is approximately `200 / 2^98 = 6.31e-28`, conditional on the string being fixed before Batch 002. This is not a circuit-specific classical null and is not, by itself, a quantum-advantage proof.

## Shot numbering

Each provider job starts its own physical shot sequence at 1. Batch 002 is therefore physically shots 1–200 of its own job. For pooled analysis only, its records may be labeled analytically as shots 201–400; the separate batch identity and job provenance must remain intact.

## Current scientific interpretation

Batch 001 currently contains a sparse collision/cluster structure with a repeated 98-bit mode and an unstable coordinate-wise majority candidate. The majority candidate remains frozen for provenance; the collision string and endpoints are separately pre-registered for Batch 002. Batch 002 is the next independent reproducibility test.
