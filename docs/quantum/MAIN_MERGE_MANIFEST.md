# Main-integration manifest

This branch is the hardware evidence source. Do not merge it blindly with
`p11_classical`.

## Retain verbatim

- `results/quantinuum/p11/quantum/`
- `results/quantinuum/p12/quantum/`
- provider and reconstruction `SHA256SUMS`
- raw provider outputs, submitted bitcode, source QASM, and job metadata

## Recommended final-main locations

- Keep immutable run evidence under `results/quantinuum/`.
- Keep general safety/reproducibility guidance under `docs/quantum/`.
- Keep reusable parsing/guard code under `src/p12_recovery/` only after
  semantic reconciliation with the classical branch.

## Likely conflicts

`README.md`, `pyproject.toml`, `Makefile`, CI workflows, shared `src/` modules,
and overlapping `docs/`/`results/` paths may conflict with `p11_classical`.
Resolve them manually; preserve both branches' provenance and do not overwrite
historical hardware artifacts with classical outputs.

## Merge order

1. Review the two branch audits and choose final-main ownership of shared code.
2. Merge or port tests and schema changes first.
3. Reconcile provider parsing, bit-order semantics, and hardware guards.
4. Merge immutable P11/P12 evidence and this manifest.
5. Resolve README/CI/pyproject conflicts manually.
6. Run offline tests, lint, type checking, checksum checks, and public audit on
   the final integration commit.
