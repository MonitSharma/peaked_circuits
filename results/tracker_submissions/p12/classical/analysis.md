# P12 200-shot Helios analysis

## Hardware run

We ran **200 shots** on Helios-1 at a reported cost of **1,373.4 HQC**. The
provider response contained five fused `END` markers. Structural repair yielded
205 diagnostic cycles and 200 reconstructed shots after excluding five exact
segment-overlap replicas.

![P12 frequency and distance histogram](../figures/frequency_and_distance.png)

## Most Frequent String

The most frequent string is the exact 98-bit string occurring most often in the
reconstructed shots:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

## Weighted Observed Medoid

The weighted observed medoid selects the observed string minimizing total
Hamming distance to the full shot distribution, with repeated strings weighted
by their frequency. It estimates the center of the noisy output cloud:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

## Cluster Consensus

Cluster consensus selects the dominant nearby cluster and computes the common
bit value at each position within that cluster:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

All three methods agreed, and the resulting bitstring was externally accepted.
