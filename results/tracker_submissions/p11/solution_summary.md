# P11 solution summary

## Hardware run

We ran **50 shots** on Quantinuum Helios-1 at a reported cost of **282.98 HQC**.
The provider framing parser reconstructed 51 records, but record 46 exactly
duplicated record 0. We removed that duplicate from the active analysis and
retained the raw reconstruction for auditability.

![P11 frequency and distance histogram](figures/frequency_and_distance.png)

## Weighted Observed Medoid

The weighted observed medoid selects the observed 98-bit string with the
smallest total Hamming distance to all 50 active shots, weighting repeated
strings by their frequency. It recovered the exact accepted answer:

```text
10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000
```

## Cluster Consensus

Cluster consensus identifies the dominant group of nearby observed strings and
computes the common bit value at each position. It independently recovered the
exact accepted answer:

```text
10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000
```

Both methods agreed, and the resulting bitstring was externally accepted.

The result is recovery evidence from hardware samples; it is not, by itself,
a quantum-advantage claim.
