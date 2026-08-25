# Batch 001 target-blind discovery summary

Batch 001 was reconstructed by excluding only the five exact segment-overlap replicas at cycle indices `37, 82, 120, 165, 201`. No hidden target, external oracle, or candidate-dependent filtering was used.

## Reconstruction

- Raw diagnostic cycles: `205`
- Excluded exact replicas: `5`
- Reconstructed shots: `200`
- Unique canonical strings: `198`
- Reconstruction manifest: `hardware_campaign/batch_001/reconstruction/reconstruction_manifest.json`

## Frozen primary candidate

Decoder: preregistered `bitwise_majority`, deterministic zero tie rule.

```text
10110001110010110111000100111100110011010110111100111101010111101111001100000000101000100000111100
```

Candidate SHA-256: `7b0c741082ffc3cfa1702fc3d9574892b1f8173f7381c149eee66a6c7b5c7403`.

The candidate is frozen as the Batch 001 discovery candidate, with `external_target_scored=false` and `target_accessed=false`. This is a protocol state transition, not a claim that the candidate is validated.

## Stability and diagnostics

- Primary candidate observed count: `0/200`.
- Most-frequent, weighted-medoid, and cluster-consensus candidates agree with one another but differ from the primary majority candidate by `13` bits.
- Decoder disagreement positions: `3, 6, 15, 26, 36, 40, 43, 44, 53, 61, 65, 71, 73`.
- 70/98 Wilson 95% intervals cross 0.5.
- The primary candidate appeared in 0/200 bootstrap modal draws under the repository’s 200-replicate bootstrap.
- No shot lies within Hamming distance 5 of the primary candidate.

These diagnostics indicate a weak/unstable discovery signal. The candidate is frozen for a future confirmation comparison, not presented as a quantum-advantage result. No confirmation hardware job was submitted.
