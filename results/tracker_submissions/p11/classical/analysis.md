# P11 corrected 50-shot Helios analysis

This is the active target-blind analysis after repairing a provider framing
artifact. The exact 51-record reconstruction is preserved under
[`raw_reconstructed_51/`](raw_reconstructed_51/); it is not silently discarded.

## Result accounting

- Requested shots: **50**
- Raw reconstructed records: **51**
- Corrected independent records used for analysis: **50**
- Repair: reconstructed record **46** was exactly identical to record **0** in
  all 98 canonical bits and was removed.
- Reported cost: **282.98 HQC**

This is a framing correction, not a claim that the provider executed 51
independent hardware shots. The raw provider metadata and text remain under
`quantum/`.

## Recovery diagnostics on the corrected data

- Mode: `00000100011010100001100110101011110000101011101010110101110111001001101001011011010001111101110010`
- Mode multiplicity: **1**
- Radius-31 cluster around the observed mode: **1** shot
- Weighted observed medoid: the externally accepted P11 string
- Cluster consensus: the externally accepted P11 string
- Mean pairwise Hamming distance: **41.911020**

Pair counts remain descriptive only because pair events are dependent; no
independent-Poisson p-values are reported.

## Provenance

- Job: `c902a6a1-0e91-48cf-b5ba-44831fcc7726`
- Device: `Helios-1`
- Repair manifest: [`raw/duplicate_frame_repair.json`](raw/duplicate_frame_repair.json)
- Raw 51-record diagnostic: [`raw_reconstructed_51/`](raw_reconstructed_51/)
- Active corrected shots: [`raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl`](raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl)

The accepted answer is retained as externally supplied scoring information;
the recovery methods themselves did not read a hidden target.
