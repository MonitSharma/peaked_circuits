# Quantum Advantage Tracker submission packages

This directory contains auditable code/results packages for the two completed
classically verifiable peaked-circuit recoveries:

- [P11 package](p11/)
- [P12 package](p12/)

Each package preserves the submitted QASM, provider metadata, raw result
artifacts, normalized shots, analysis reports, timing information, and a
machine-readable tracker record. The package is designed to support a tracker
submission and independent audit without credentials or access to the provider
API.

The results establish successful recovery of the accepted bitstrings. They do
not, by themselves, establish a quantum-advantage claim. Quantum and classical
runtime/resource fields are reported separately, and any missing timing is
marked as not retained rather than estimated.

Run the repository-level integrity check with:

```bash
python3 tools/verify_tracker_packages.py
```

To recompute the core target-blind mode, bitwise-majority, and weighted
observed-medoid results from the packaged shots:

```bash
python3 tools/reproduce_tracker_recovery.py
```

To regenerate the supporting frequency/distance figures:

```bash
python3 tools/generate_tracker_plots.py
```

The tracker issue drafts are in [TRACKER_ISSUE_TEMPLATE.md](TRACKER_ISSUE_TEMPLATE.md).
To re-run the classical recovery and measure local runtime:

```bash
.venv/bin/python tools/run_tracker_classical_audit.py p11 p12
```
