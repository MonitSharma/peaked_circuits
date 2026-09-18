# Repository audit — `p12_quantum`

Audit date: 2026-09-01. This audit is offline-only and records the state before
the publication curation work in this goal.

## Git and scope

| Item | Value |
|---|---|
| Branch | `p12_quantum` |
| HEAD before this curation | `012f903ccc456e18c9431cd83e41163a9400bf9c` |
| Remote | `https://github.com/MonitSharma/p12-helios-recovery.git` |
| Remote branch | `origin/p12_quantum` |
| Initial status | Branch matched origin; unrelated untracked P6/P8 work was present |
| Scope | P11/P12 Quantinuum evidence and offline documentation only |
| Remote jobs | None submitted in this curation |

The pre-existing untracked files were preserved and are not included in this
curation. No `main` or `p11_classical` files were modified.

## Runtime and dependencies

- Python: 3.12.9 from `.venv`
- Project: `p12-helios-recovery` 0.1.0
- pytest 9.1.1; ruff 0.16.4; mypy 2.3.1
- pytket 2.18.1; pytket-quantinuum 0.59.2; pytket-qir 2.0.0; qnexus 0.46.0
- numpy 2.5.2; scipy 1.18.1; matplotlib 3.11.1

## Repository inventory

Relevant top-level areas are `circuits/`, `configs/`, `data/`, `docs/`,
`hardware_campaign/`, `results/`, `schemas/`, `scripts/`, `src/`, `tests/`,
and `tools/`. The source implementation is under `src/p12_recovery`; CI is
defined in `.github/workflows/ci.yml` plus separate syntax-check and emulator
workflow files.

## Existing verification surface

The repository has offline pytest coverage for bit ordering, provider result
normalization, recovery, QIR validation, campaign state, cost protocols,
hardware/emulator guards, and reporting. CI runs ruff, mypy, pytest excluding
hardware/integration markers, schema checks, synthetic smoke tests, mapping
checks, QIR validation, and public-audit checks.

The physical submission boundary is fail-closed: ordinary commands do not
submit hardware, and the hardware guard retains an unconditional paid-execution
block in the current milestone. Historical provider artifacts are data, not
authorization to run again.

## Audit conclusion

The branch contains sufficient retained evidence to build separate P11 and P12
hardware narratives. Historical provider metadata contains hardware timing and
cost fields; classical-analysis elapsed time was not retained. That missing
value is carried forward as `not recorded`.
