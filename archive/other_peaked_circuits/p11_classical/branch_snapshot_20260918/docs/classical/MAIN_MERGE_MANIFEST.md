# Main merge manifest

This branch is `p11_classical`; it has not been merged into `main`.

## New canonical navigation

- `problems/P1/CANONICAL.md`, `P5/CANONICAL.md`, `P6/CANONICAL.md`,
  `P8/CANONICAL.md`, `P9/CANONICAL.md`, and `P11/README.md`.
- `problems/P6/METHOD_MATRIX.md` and `CLASSICAL_EXHAUSTION_SUMMARY.md`.
- `docs/classical/` overview, controls, audit, reproducibility, and figures.
- `results/classical_index.json` and its validator/test.

## Likely conflict points

`README.md`, `problems/README.md`, `results/README.md`, and long P5/P6/P8/P9
reports may also be edited by later branches. During integration, preserve the
classical status language—especially P6 `UNRESOLVED`—and keep hardware-specific
workflows and reports from the target branch.

## Recommended merge order

1. Merge canonical problem pages and P6 matrix.
2. Merge `docs/classical/` and the results index/validator.
3. Resolve the top-level README and shared index manually.
4. Run the target branch's CI and retain hardware-specific files from the
   hardware branch where they overlap.

Do not overwrite provider credentials, hardware workflows, or raw result trees.
