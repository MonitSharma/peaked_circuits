# P12 solution summary

## Hardware run

We ran **200 shots** on Quantinuum Helios-1 at a reported cost of **1,373.4
HQC**. The malformed provider framing was repaired structurally: 205
diagnostic cycles produced 200 reconstructed shots after five exact
segment-overlap replicas were excluded.

![P12 frequency and distance histogram](figures/frequency_and_distance.png)

## Most Frequent String

This is the exact 98-bit string with the highest observed frequency:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

## Weighted Observed Medoid

This method selects the observed string with the smallest total Hamming
distance to the full shot distribution, weighting repeated strings by their
frequency. It estimates the center of the noisy output cloud:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

## Cluster Consensus

This method selects the dominant nearby cluster and computes the common bit
value at each position within that cluster:

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

All three methods agreed, and this bitstring was externally accepted.

The result is recovery evidence from hardware samples; it is not, by itself,
a quantum-advantage claim.
