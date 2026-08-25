# Batch 002 Helios-1 confirmation plan

Status: prepared, not submitted.

## Purpose

Batch 002 is an independent confirmation of the frozen Batch 001 discovery candidate. It must be analyzed independently before any pooling or decision about a third batch.

## Frozen inputs

- Branch: `p12_quantum`
- Circuit: `peaked_circuit_P12_Hqap_98x2457`
- Target: physical `Helios-1`
- Requested shots: exactly `200`
- Batch role: `confirmation`
- Batch 001 candidate freeze hash: `7b0c741082ffc3cfa1702fc3d9574892b1f8173f7381c149eee66a6c7b5c7403`
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
4. Compute its bitwise-majority candidate, per-bit margins, Wilson intervals, exact-binomial tests with BH/FDR and Holm corrections, decoder diagnostics, Hamming basins, split-half stability, random-subsample Hamming distributions, bootstrap stability, and provider-order blocks.
5. Compare Batch 002 with the frozen Batch 001 candidate and record Hamming distance and anchor-bit agreement.
6. Only after independent analysis, compute the pooled 400-shot candidate.
7. Decide whether Batch 003 is warranted using the predeclared rules below.

## Decision rules

- Do not use hidden-target scoring, external oracle feedback, or adaptive candidate selection.
- Do not call Batch 001 or Batch 002 a validated answer based on one majority string alone.
- Favor stopping after Batch 002 if the two independent candidates agree closely, stability improves materially, and anchor bits replicate.
- Consider Batch 003 only if Batch 002 is directionally consistent but still noisy, with disagreements concentrated in low-margin positions.
- Stop and diagnose rather than automatically spending Batch 003 if Batch 002 strongly disagrees with Batch 001 or shows a different distributional structure.

## Shot numbering

Each provider job starts its own physical shot sequence at 1. Batch 002 is therefore physically shots 1–200 of its own job. For pooled analysis only, its records may be labeled analytically as shots 201–400; the separate batch identity and job provenance must remain intact.

## Current scientific interpretation

Batch 001 currently contains detectable aggregate marginal structure but an unstable discovery candidate. Its candidate is frozen as a hypothesis, not validated. Batch 002 is the next independent reproducibility test.
