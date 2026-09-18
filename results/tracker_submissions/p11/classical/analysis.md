# P11 corrected 50-shot Helios analysis

## Hardware run

We ran **50 shots** on Helios-1 at a reported cost of **282.98 HQC**. The raw
provider framing reconstructed 51 records, but record 46 was an exact duplicate
of record 0. The duplicate was removed from the active analysis, leaving 50
records. The raw 51-record reconstruction remains under
[`raw_reconstructed_51/`](raw_reconstructed_51/).

![P11 frequency and distance histogram](../figures/frequency_and_distance.png)

## Weighted Observed Medoid

The weighted observed medoid selects the observed string with the smallest
total Hamming distance to all active shots, weighting repeated strings by their
frequency. It recovered the exact accepted answer:

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

Both methods agreed. The recovery methods were target-blind; external scoring
later accepted this bitstring.
