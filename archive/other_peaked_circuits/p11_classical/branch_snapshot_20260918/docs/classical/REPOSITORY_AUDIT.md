# Classical branch repository audit

**Audit date:** 2026-09-01  
**Branch:** `p11_classical`  
**HEAD:** `ce098ca477fc6fa66828f08e7499055b46ee8560`

## Scope and guardrails

This is the Phase 0 audit required before curation. It covers the working tree
as found, without deleting or rewriting raw evidence. The curation work is
documentation, indexing, validation, and deterministic figure generation; it
does not launch simulations, hardware jobs, portal submissions, or cloud work.

## Repository snapshot

The branch tracked the remote branch at audit time. The worktree had no
modified tracked files, but it contained untracked bundles, result directories,
logs, caches, and exploratory scripts. Those were deliberately left untouched
and are not implicitly part of the curation commits.

| Item | Observation |
|---|---|
| Python reported by `python3` | 3.13.7 |
| Project validation environment | `.venv` |
| Files under `results/` | 2,197 |
| Files under `docs/` | 77 |
| Files under `scripts/` | 169 |
| Files under `tests/` | 115 |
| Files under `problems/` | 21 |
| CI workflows | `ci.yml`, `helios-syntax-check.yml`, `helios-emulator-mapping.yml` |

## Top-level inventory

The repository contains source packages (`src/`, `compiler/`, `structural/`),
problem inputs (`circuits/`, `data/`, `problems/`), experiment and solver
launchers (`scripts/`, `experiments/`, `hpc/`, `julia/`), raw and curated
evidence (`results/`, `docs/`), tests (`tests/`), schemas, and project metadata.
The new canonical pages add navigation without moving the large historical
result tree.

## Existing automation

`ci.yml` runs offline lint, typing, tests, schema checks, and selected smoke
checks on pushes and pull requests. The two Helios workflows are manually
guarded and self-hosted; they are not part of routine classical reproduction.

## Baseline validation

The system Python did not expose `pytest`, `ruff`, or `mypy`; the repository
virtualenv does. Baseline commands were therefore run through `.venv/bin/`.
The exact outcomes are recorded here as the audit baseline and updated in the
final curation report after the new validator and documentation checks run:

| Check | Baseline outcome |
|---|---|
| `.venv/bin/pytest -q -m 'not hardware and not integration'` | 214 passed, 2 warnings |
| `.venv/bin/ruff check .` | non-zero; pre-existing findings across historical scripts/results |
| `.venv/bin/mypy src` | non-zero; 101 pre-existing errors across 26 source files |

The broad lint command intentionally sees historical scripts and result-bundle
launchers. The curation changes do not mass-reformat those files because that
could alter or obscure historical evidence.

## Required source review

The audit review included the branch landing page, problem index, P5/P6/P8
campaign and fidelity-calibration reports, P6 MPO/representation/invariant/
Pauli/SOP feasibility records, P8 method and forensic history, P5/P6/P8/P9
problem pages and manifests, and the P11 classical campaign reports. Where
historical reports use different experimental checkpoints, the canonical pages
identify the selected artifact and preserve the older record as history.

## Curation policy

Canonical pages are entry points, not replacements for long reports. Numeric
claims must point to a retained artifact or be labelled `not recorded`.
`METHOD_EXHAUSTED` means exhausted within the tested method families and
available resources; it is never a claim of mathematical impossibility.
