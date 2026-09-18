# Classical reproducibility guide

## Environment

Use the repository virtualenv or a clean Python environment matching
`pyproject.toml`. The external P9 solver has a separate Python 3.10 constraint;
do not assume the project Python and solver Python are interchangeable.

```bash
python3 -m venv .venv-local
.venv-local/bin/pip install -e '.[dev]'
.venv-local/bin/pytest -q -m 'not hardware and not integration'
```

## Lightweight validation

Run the index validator and tests first. Inspect the canonical pages and raw
manifests before attempting any long run. P5 and P9 are the recommended
positive controls; compare fidelity, peak fraction, and separation, not only
gate counts.

```bash
.venv/bin/python scripts/validate_classical_index.py
.venv/bin/pytest -q tests/test_classical_index.py
```

## Evidence inspection

P6 raw evidence is under `results/p5_p6_p8_recovery/P6/` and summarized in
`problems/P6/`. P8's validated tail candidate is under
`results/p5_p6_p8_recovery/P8/tail804_7296a2a/`. Historical paths are retained;
the curated index is navigation, not a replacement for raw artifacts.

## Expensive reproduction

The P5/P9 controls and P8 tail path can require minutes to hours depending on
backend and memory. P6/P11 exploratory runs are resource-intensive and should
be bounded, logged, and run only with explicit capacity. No hardware, cloud,
portal, or overnight job is required for the documentation validation.

## Provenance rules

Record source QASM SHA-256, solver commit, environment, seed, cutoff, bond
limit, sample count, and validation status. Never use supplied overlap scores to
tune candidate generation; label any later comparison oracle-assisted.
