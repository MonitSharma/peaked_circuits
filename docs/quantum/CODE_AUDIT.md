# Code and data-pipeline audit

The audit focused on behavior relevant to the retained P11/P12 evidence.

## Findings

- Provider-specific parsing is isolated in `provider_results.py`,
  `nexus_results.py`, and `nexus_hardware.py`; canonical bitstrings are handed
  to the analysis layer only after width/order checks.
- Bit order is explicit in `bit_ordering.py` and `provider_mapping.py`; silent
  reversal is rejected.
- Hardware/emulator authorization is separated into guard modules and covered
  by tests. The current physical path is fail-closed.
- Historical P12 reconstruction is preserved as an evidence artifact and is
  documented rather than rewritten.
- Deterministic JSON serialization and SHA-256 provenance are provided by the
  reporting/hashing utilities and the retained manifests.
- No new provider parser or reconstruction rewrite was necessary for this
  curation; additional documentation and an index test provide the requested
  audit surface without changing historical behavior.

## Remaining maintenance items

The repository-wide ruff run has six pre-existing findings in older provider and
utility files (explicit `zip(strict=...)`, import ordering, and an ambiguous
Unicode dash). They are outside the evidence curation and were not changed to
avoid unrelated behavioral edits. Mypy passes for all 43 source files, and the
offline test suite passes.

## Test coverage added here

`tests/test_hardware_index.py` checks the machine-readable P11/P12 index,
required fields, source/result/analysis paths, and the checked-in schema's key
invariants. It uses only the filesystem and does not contact a provider.
