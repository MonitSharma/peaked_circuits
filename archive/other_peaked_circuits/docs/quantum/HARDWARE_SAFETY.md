# Hardware safety

This branch contains historical hardware evidence but the default workflows
are offline. No command in this curation submits a job.

## Controls

- Physical execution has a separate code path from compilation, syntax checks,
  and emulator work.
- The physical guard requires explicit environment authorization, an execution
  flag, readiness checks, typed confirmation, target classification, positive
  cost evidence, and a cost ceiling.
- The current hardware submission boundary remains fail-closed even when those
  inputs are supplied; ordinary CI cannot submit paid hardware work.
- Syntax-check and emulator targets are validated separately from physical
  `Helios-1`.
- Credentials are read from the environment/provider login flow and must never
  be committed. `.env`, Nexus caches, and raw credentials are excluded by the
  public-audit policy.
- Historical job IDs and result files are evidence only, not permission to
  retrieve or rerun jobs.

## Safe operating model

Use `pytest -m 'not hardware and not integration'`, local QASM/QIR validation,
saved-result import, and report generation for offline work. Review target and
cost evidence before any future remote operation. Never remove the explicit
physical target and cost gates to make a command convenient.
