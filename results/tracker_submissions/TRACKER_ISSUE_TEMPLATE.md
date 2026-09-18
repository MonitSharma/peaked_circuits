# Quantum Advantage Tracker issue templates

These are submission drafts for the existing classically verifiable problem
entries. They follow the field order used by the tracker’s classically
verifiable submission issues. Replace the repository/package links after this
repository is public and pushed.

The result should be described as a verified recovery submission, not as a
quantum-advantage claim. The tracker issue should link to the complete package,
the source QASM, raw results, measured classical runtime, and the diagnostic
figure.

## P11 issue body

```markdown
### Name

Quantum Solution for peaked_circuit_P11_Hqap_98x1999

### Circuit

peaked_circuit_P11_Hqap_98x1999

### Value

100%

### Method

Quantinuum Helios-1 hardware; deterministic classical recovery from 51 returned 98-bit records using weighted observed medoid and cluster consensus.

### Method proof

Complete reproducibility package:
https://github.com/MonitSharma/p12-helios-recovery/tree/p12_quantum/results/tracker_submissions/p11

The package includes the exact submitted QASM, provider job metadata, raw provider result, canonical shot records, SHA256 manifests, the recovery implementation, measured classical runtime, and plots. The provider job ID was `c902a6a1-0e91-48cf-b5ba-44831fcc7726`; 50 shots were requested and 51 complete records were returned. The recovered 98-bit string was:

`10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000`

The weighted observed medoid and cluster consensus reproduce the externally accepted string. The simple observed mode does not. The frequency plot is therefore descriptive rather than evidence of a large exact-string peak.

### Authors

Monit Sharma

### Institutions

Independent researcher

### Quantum runtime (seconds)

229.924343

### Classical runtime (seconds)

0.007269500

### Compute resources (quantum)

Quantinuum Helios-1

### Compute resources (classical)

Apple Silicon Mac; local Python implementation in `src/p12_recovery/recovery.py`.

### Notes

Recovery submission; no quantum-advantage claim.
```

## P12 issue body

```markdown
### Name

Quantum Solution for peaked_circuit_P12_Hqap_98x2457

### Circuit

peaked_circuit_P12_Hqap_98x2457

### Value

100%

### Method

Quantinuum Helios-1 hardware; deterministic reconstruction and classical recovery from 200 normalized records using mode, weighted observed medoid, and cluster consensus.

### Method proof

Complete reproducibility package:
https://github.com/MonitSharma/p12-helios-recovery/tree/p12_quantum/results/tracker_submissions/p12

The package includes the exact submitted QASM, provider job metadata, byte-preserved raw result, the repaired framing artifact, reconstruction manifest, normalized shots, SHA256 manifests, the recovery implementation, measured classical runtime, and plots. The provider job ID was `d5cba0df-a7aa-459e-ac51-8092645c059f`; 200 normalized shots were reconstructed from a response containing 205 framed cycles and five excluded segment-overlap replicas. The recovered 98-bit string was:

`10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100`

The mode, weighted observed medoid, and cluster consensus agree on the externally accepted string. Bitwise majority differs at 13 positions. The frequency plot is descriptive supporting evidence, not a hidden-target lookup.

### Authors

Monit Sharma

### Institutions

Independent researcher

### Quantum runtime (seconds)

237.588

### Classical runtime (seconds)

0.016120542

### Compute resources (quantum)

Quantinuum Helios-1

### Compute resources (classical)

Apple Silicon Mac; local Python implementation in `src/p12_recovery/recovery.py`.

### Notes

Recovery submission; no quantum-advantage claim.
```
