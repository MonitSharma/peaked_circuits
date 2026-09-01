# Quantum reproducibility

## Fully reproducible offline

From the committed source and saved evidence, an auditor can reproduce QASM
inspection, local QIR structural validation, bit-order/mapping checks, saved
result normalization, P12 framing reconstruction, canonical counts, collision
analysis, candidate algorithms, validation reports, the hardware index, and
the figures. These operations do not require credentials or paid execution.

Representative commands:

```bash
source .venv/bin/activate
pytest -q -m 'not hardware and not integration'
ruff check .
mypy src
p12-recovery inspect
p12-recovery validate
p12-recovery validate-qir --input results/qir/p12.ll
p12-recovery build-report
```

Commands that generate files should be run in a disposable checkout or with
their output paths reviewed first. Historical raw artifacts under
`results/quantinuum/` are not inputs to a provider call.

## Credentials but no paid execution

The repository supports provider discovery, syntax-check/cost evidence, and
retrieval of an already-existing job only where the corresponding command is
explicitly invoked and authorized. This document does not claim that every
provider API operation is currently available offline; consult the command's
guard and saved evidence before use.

## Historical paid hardware steps

P11 and P12 hardware submission and execution occurred before this package was
curated. Their job IDs, source artifacts, provider responses, costs, timing,
and derived data are preserved. Do not rerun them to reproduce the historical
record. Reproduction here means re-running the deterministic local analysis on
the saved result.
