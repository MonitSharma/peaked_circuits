# P11 solution summary

## Hardware and classical procedure

The 50-shot Helios-1 result was preserved verbatim, normalized into complete
98-bit records, and analyzed independently of any hidden target. The retained
analysis computed the mode, radius-31 cluster, cluster-restricted majority,
Hamming diagnostics, bootstrap output, and recovery metadata. The observed
mode/cluster was weak, so this batch is evidence of an exploratory hardware
sample rather than a target-blind proof of the answer.

## Reported answer

The following bitstring was supplied later as the externally scored P11 answer:

```text
10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000
```

This is labeled as externally reported because the retained P11 analysis file
does not contain a hidden-target lookup or an external score. It must not be
presented as a result of target-blind statistics alone.

## Reproducibility boundary

The raw provider payload, normalized shots, submitted input, source hash, QIR
hash, job metadata, and analysis outputs are all retained under this folder.
No quantum-advantage claim is made here.

## Positive-control audit (2026-09-07)

The saved canonical shot records were reanalysed locally, without provider
access, additional HQC spend, or hidden-target lookup. Weighted observed
medoid and cluster consensus both recovered the externally accepted string
exactly. Bitwise majority was one bit away; the simple frequency mode was 37
bits away. This confirms that the medoid/cluster recovery pipeline can recover
the accepted P11 answer from the retained data, while also showing why the
simple mode should not be treated as decisive.

The machine-readable audit is retained at
`results/quantinuum/positive_control_audit_20260907/audit.json` and the
summary at `results/quantinuum/positive_control_audit_20260907/audit.md`.
