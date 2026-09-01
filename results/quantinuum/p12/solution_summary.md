# P12 solution summary

## Hardware and classical procedure

The completed Helios-1 job was retrieved without rerunning it. The malformed
result framing was repaired structurally, not by candidate-dependent filtering:
205 diagnostic cycles were identified, five exact segment-overlap replicas were
excluded, and 200 canonical shots were reconstructed. The raw provider result
and every reconstruction step are retained in this package.

The candidate analysis compared four decoders. Most-frequent, weighted
observed medoid, and cluster consensus agreed; coordinate-wise majority differed
by 13 bits and was retained as a separate frozen discovery candidate. Collision
pair counts are descriptive only, and the validation report records split-half,
bootstrap, framing-sensitivity, and independent-rerun checks.

## Final answer

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

This is the answer associated with the agreeing medoid/cluster-consensus
analysis and the later external verification reported in the project history.
The result is recurrence/recovery evidence; it is not, on its own, a
quantum-advantage claim.

## Reproducibility boundary

The source circuit, submitted artifact, provider metadata, raw result, repaired
framing, reconstructed 200-shot dataset, hashes, analysis, and validation
records are all retained under this folder.
