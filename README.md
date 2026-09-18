# Peaked Circuit — P11/P12 quantum recovery

This repository is the focused research record for the two important peaked
circuits run on Quantinuum Helios-1:

| Problem | Hardware run | Result |
|---|---|---|
| P11 | 50 requested shots; 51 returned | Externally accepted 98-bit recovery |
| P12 | 200 reconstructed shots | Externally accepted 98-bit recovery |

The repository is intentionally focused on the quantum runs and their
auditable evidence. Earlier P11 classical experiments and all other peaked
circuits are preserved, but moved to
[archive/other_peaked_circuits/](archive/other_peaked_circuits/).

## Start here

- [P11 overview](problems/P11/README.md)
- [P12 overview](problems/P12/README.md)
- [P11 evidence package](results/tracker_submissions/p11/)
- [P12 evidence package](results/tracker_submissions/p12/)
- [Tracker issue drafts](results/tracker_submissions/TRACKER_ISSUE_TEMPLATE.md)
- [Archive index](archive/other_peaked_circuits/README.md)

Each active package contains the exact QASM, provider job metadata, raw
results, normalized shots, plots, recovery reports, timing records, runtime
measurements, and SHA256 manifests. The package is designed for external
review without provider credentials or another hardware submission.

## Reproduce the local analysis

Python 3.11 or newer is required. From the repository root:

```bash
.venv/bin/python tools/verify_tracker_packages.py
.venv/bin/python tools/reproduce_tracker_recovery.py
.venv/bin/python tools/run_tracker_classical_audit.py p11 p12
```

These commands are offline-only. They do not contact Quantinuum, consume HQC,
or read credentials. The public CLI is `peaked-circuit`; the historical
`p12_recovery` Python package name and `p12-recovery` CLI are retained for
compatibility with the implementation.

## Interpretation boundary

The accepted bitstrings document successful recovery of the classically
verifiable answers. They do not, by themselves, establish a quantum-advantage
claim. Quantum runtime, classical runtime, resource descriptions, raw
provider framing, and candidate-recovery evidence are reported separately.
