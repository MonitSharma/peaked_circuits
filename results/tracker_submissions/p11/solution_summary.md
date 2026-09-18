# P11 solution summary

## Hardware and classical procedure

The 50-shot Helios-1 result was preserved verbatim, reconstructed into 51
complete 98-bit records by the provider framing parser, and audited for
duplicates. Reconstructed record 46 exactly duplicated record 0, so it was
removed from the active 50-shot analysis while the raw 51-record reconstruction
was retained. The corrected analysis computed the mode, Hamming diagnostics,
and deterministic recovery methods independently of any hidden target.

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
