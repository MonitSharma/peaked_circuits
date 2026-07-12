# P12 Helios Recovery

This repository is a research-grade, independent feasibility and reproducibility pipeline for
recovering the hidden peak of Quantum Advantage Tracker circuit
`peaked_circuit_P12_Hqap_98x2457` (98 qubits; 2,457 registered gates). The scientific question is
whether a transparent, preregistered Quantinuum execution and post-processing protocol can recover
the target bits. **Milestone 1 never submits hardware jobs, consumes HQCs, requests credentials, or
claims that the hidden peak has been solved.**

## Set up

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
# Optional compile-only SDK support:
python -m pip install -e '.[quantum]'
```

## Reproduce Milestone 1

```bash
p12-recovery doctor
p12-recovery fetch
p12-recovery inspect
p12-recovery synthetic --config configs/synthetic.yaml
pytest -q -m 'not hardware'
ruff check .
mypy src
p12-recovery compile --config configs/compilation.yaml  # only with optional SDK and target
p12-recovery validate
p12-recovery build-report
```

Or run `make milestone-1`. Compilation produces a structured blocked report when no configured
Quantinuum target or required access is available. Hardware execution is not a CLI command.

## Canonical bit order

A canonical candidate has 98 characters. Position `i` is logical qubit `q[i]`: `q[0]` is the
leftmost character and `q[97]` is the rightmost. Provider strings are never silently reversed.
Conversion requires an explicit logical-to-classical map, provider display order, and classical
register layout; ambiguity is an error. See [docs/bit_ordering.md](docs/bit_ordering.md).

## Recovery and reproducibility

The primary method is bitwise majority. Most-frequent observation, weighted observed medoid, and
hierarchical-cluster consensus are registered secondary methods. Synthetic independent, asymmetric,
correlated-burst, and mixture noise are deterministic under explicit seeds. Important inputs and
generated circuit artifacts are SHA-256 hashed; JSON reports accompany Markdown summaries; every
artifact-producing CLI operation writes a run manifest.

## Repository map

- `circuits/original`: byte-preserved source, checksum, and acquisition metadata
- `src/p12_recovery`: importable implementation and backend adapters
- `configs`: inspection, compilation, synthetic, and experiment snapshots
- `results`: generated reports, figures, compilation artifacts, and manifests
- `schemas`: Pydantic-generated report schemas
- `tests`: offline unit tests plus separately marked integration/hardware tests
- `docs`: research question, draft protocol, interpretation, and readiness checklists

## Hardware safety

Credentials alone can never trigger submission. The central guard checks the CLI flag, two explicit
environment values, interactive confirmation, target mode, and readiness—and then still blocks,
because Milestone 1 deliberately contains no functioning submission implementation. Never store
credentials in this repository.

## Limitations

Full 98-qubit statevector simulation is intentionally excluded. QASM round-trip and small-circuit
semantic checks do not establish full P12 semantic equivalence. A successful parse does not imply
backend validity. Hardware executability may only be claimed after a configured current target's
predicates pass. Accuracy against the real hidden target is unavailable locally.

## Citation

Use `CITATION.cff`. The upstream QASM remains the work of its original authors and is identified by
its Tracker commit, path, retrieval time, and SHA-256 digest.

