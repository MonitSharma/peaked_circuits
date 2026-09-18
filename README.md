# P12 Helios Recovery — `p12_quantum`

> **Branch:** `p12_quantum`  
> **Scope:** Offline-auditable Quantinuum Helios hardware recovery records for P11 and P12.

This branch preserves the source circuits, compiled artifacts, provider jobs, raw results,
canonical shots, recovery analyses, costs, and timing evidence for the completed P11 and P12
Helios-1 runs. Successful recovery is not itself a quantum-advantage claim.

The software is Monit Sharma's recovery and reproducibility pipeline. The byte-preserved P12 QASM is
an upstream Quantum Advantage Tracker artifact; the circuit construction and scientific work remain
attributable to their original authors. Including it does not claim authorship of the circuit.

## Headline hardware results

| Problem | Backend | Shots | Cost | Outcome |
|---|---|---:|---:|---|
| P11 | Helios-1 | 50 requested / 51 returned | 282.98 HQC | Weak exploratory cluster; later external answer reported |
| P12 | Helios-1 | 200 reconstructed | 1,373.4 HQC | Three observed-data decoders agreed; later external verification reported |

See the [problem archive](problems/README.md), the canonical
[`P11 page`](problems/P11/README.md), and [`P12 page`](problems/P12/README.md).

For tracker submission packages containing the exact QASM, provider artifacts,
normalized shots, plots, measured classical runtimes, and issue drafts, see
[`results/tracker_submissions/`](results/tracker_submissions/).

## Branch scope and historical implementation

Milestone 2 adds authenticated Nexus/Helios discovery, legacy local exact-target compilation,
permutation-safe measurement tracing, saved-result import, canonical normalization, deterministic
mapping circuits, cost-evidence reporting, protocol freeze gates, evidence-based readiness, and a
public-release audit. The Helios HUGR/QIR transition is detected and blocked rather than routed
through the obsolete H-series interface. Paid hardware execution remains disabled.

Milestone 3 adds deterministic P12 QIR export, LLVM/pyqir validation, an explicit 98-entry
logical-to-QIR result map, six reversal-sensitive QIR mapping cases, and a separately guarded
`Helios-1SC` Nexus syntax-check path. It does not execute `Helios-1E` or `Helios-1`, does not resolve
provider result order, and cannot claim hardware readiness.

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

## CPU simulation

The project includes a launcher for the public MPO + unswapping CPU solver used in [QAT issue #153](https://github.com/quantum-advantage-tracker/quantum-advantage-tracker.github.io/issues/153).
The recommended starting point is macOS, using the reproducible setup and P9
benchmark in [docs/mac_mpo_workflow.md](docs/mac_mpo_workflow.md):

```bash
bash scripts/setup_mac.sh
source .venv-mpo-mac/bin/activate
bash scripts/benchmark_p9_mac.sh
```

The setup installs the main development environment plus compile-only quantum
SDKs; it does not submit hardware jobs or consume HQCs.

The launcher never submits hardware work. Server-specific installation and
bounded P12 trial commands are in [docs/cpu_mpo_simulation.md](docs/cpu_mpo_simulation.md).

## Canonical bit order

A canonical candidate has 98 characters. Position `i` is logical qubit `q[i]`: `q[0]` is the
leftmost character and `q[97]` is the rightmost. Provider strings are never silently reversed.
Conversion requires an explicit logical-to-classical map, provider display order, and classical
register layout; ambiguity is an error. See [docs/bit_ordering.md](docs/bit_ordering.md).

## Historical Milestone 2 workflow

```bash
python -c "import qnexus as qnx; qnx.login()"  # browser login; do not paste credentials
p12-recovery devices --only-p12-compatible
export P12_QUANTINUUM_DEVICE="<exact-discovered-device-name>"
# For Helios, review docs/helios_nexus.md and stop before any remote write/job.
p12-recovery compile --config configs/compilation.yaml
p12-recovery validate
p12-recovery mapping-check --target "$P12_QUANTINUUM_DEVICE" --mode emulator
p12-recovery estimate-cost --target "$P12_QUANTINUUM_DEVICE" --shots 20,100,250,500,1000,2000
p12-recovery freeze-protocol
p12-recovery build-report
p12-recovery public-audit
```

Run `freeze-protocol` only after Tracker evaluation rules are confirmed. It requires a clean commit
and complete target, mapping, cost, and protocol evidence.

### Discovery and target-specific compilation

`devices` merges two distinct official SDK surfaces. It uses authenticated
`qnexus.devices.get_all()` for current Nexus/Helios access and retains
`QuantinuumBackend.available_devices()` only as legacy H-series metadata whose account access is
explicitly unverified. Helios names are passed as `system_name` to
`qnexus.models.HeliosConfig`; H-series configuration uses `device_name`. Target names must match
authenticated Nexus discovery exactly. CLI `--target` overrides configuration, which overrides
`P12_QUANTINUUM_DEVICE`. Compilation verifies SDK support for `preserve_qubit_names=true` and
`allow_implicit_swaps=false`, records `CompilationUnit.initial_map/final_map`, and fails on an unknown
permutation.

The current Milestone 2 `compile` command never uploads a circuit or starts a Nexus job. A Helios
target therefore produces a structured blocker until a separately guarded HUGR/QIR Nexus compilation
workflow is implemented and explicitly authorized. See [docs/helios_nexus.md](docs/helios_nexus.md).

### Result import and mapping circuits

`import-quantinuum-result` retrieves only an existing job or reads a saved raw result. Raw and
canonical data are stored separately, and recovery receives only exact 98-bit canonical counts after
order, layout, mapping, width, and shot-total validation. `mapping-check` creates six endpoint,
sparse, block, and alternating patterns that expose reversals. It can compile them but does not submit
them; imported emulator observations are needed to finish validation.

### Cost, readiness, and public audit

Cost reports contain only provider-supported evidence; an unavailable API produces `unsupported`,
never an invented HQC formula. Readiness is derived from hashed evidence and is capped at
`READY_FOR_EMULATOR_MAPPING_VALIDATION`; hardware readiness is not exposed. `public-audit` checks
credentials, tokens, local paths, private raw metadata, citation, license, and report provenance
without changing repository visibility.

## Historical Milestone 3 local workflow

```bash
p12-recovery export-qir \
  --source circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm \
  --output results/qir/p12.ll
p12-recovery validate-qir --input results/qir/p12.ll
p12-recovery export-mapping-qir
p12-recovery build-report
p12-recovery public-audit
```

The exporter uses the official `pytket-qir` API with the base QIR profile. Because the converter
limits each classical register to 64 bits, the canonical output is represented by 98 explicit
one-bit result registers. Each logical `q[i]` is locally verified against QIR qubit/result `i`, while
`provider_result_position` stays null.

The optional remote command is intentionally double-armed and fixed to the free syntax checker:

```bash
export P12_ENABLE_NEXUS_SYNTAX_CHECK=1
p12-recovery nexus-syntax-check --target Helios-1SC --mapping-cases --submit-syntax-check
p12-recovery nexus-syntax-check --target Helios-1SC --qir results/qir/p12.ll --submit-syntax-check
```

Do not substitute `Helios-1E` or `Helios-1`; the guard refuses both. See
[docs/milestone_3.md](docs/milestone_3.md).

Milestone 4 adds a separate cost-capped emulator boundary:

```bash
p12-recovery nexus-cost --target Helios-1E --mapping-cases --shots 3
export P12_ENABLE_HELIOS_EMULATOR=1
p12-recovery emulator-mapping-check --target Helios-1E --shots 3 --max-cost 6.0 --execute-emulator
```

Six jobs resolved all 98 labeled Nexus positions. `Helios-1` remains impossible through these
commands. The optional `p12-emulator-pilot` is capped at 20 shots and remains unrun. See
[docs/milestone_4.md](docs/milestone_4.md).

## How recovery works

The pipeline fixes logical bit order, preserves provider framing, normalizes shots, and applies
target-blind mode, Hamming/cluster, weighted-medoid, majority, bootstrap, and stability diagnostics.
P12's most-frequent, weighted-medoid, and cluster-consensus methods agreed. P11's observed
recurrence was weak. Pair counts are descriptive only because pair events are dependent.

## Offline reproduction and safety

See [`REPRODUCIBILITY_QUANTUM.md`](REPRODUCIBILITY_QUANTUM.md),
[`docs/quantum/HARDWARE_SAFETY.md`](docs/quantum/HARDWARE_SAFETY.md), and
[`docs/quantum/QUANTINUUM_RESEARCH_OVERVIEW.md`](docs/quantum/QUANTINUUM_RESEARCH_OVERVIEW.md).
Default CI and ordinary commands do not submit paid hardware jobs.

## Repository map

- `circuits/original`: byte-preserved source, checksum, and acquisition metadata
- `src/p12_recovery`: importable implementation and backend adapters
- `configs`: inspection, compilation, synthetic, and experiment snapshots
- `results`: generated reports, figures, compilation artifacts, and manifests
- `schemas`: Pydantic-generated report schemas
- `tests`: offline unit tests plus separately marked integration/hardware tests
- `problems/P11`, `problems/P12`: canonical problem pages
- `results/quantinuum`: organized hardware evidence and machine-readable index
- `docs/quantum`: research narrative, lineage, safety, figures, interpretation, and merge guidance

## Hardware safety

Credentials alone can never trigger submission. Syntax, emulator, and future hardware work have
separate guards. Emulator execution requires exact target discovery, cost evidence, a positive
per-job ceiling, environment authorization, a CLI flag, and confirmation. Never store credentials
in this repository.

## Limitations

Full 98-qubit statevector simulation is intentionally excluded. Classical-analysis wall time was
not retained for the historical hardware runs. QASM/QIR validation and saved-result analysis do not
establish a quantum-advantage claim; comparable classical resource accounting remains necessary.

## Citation

Use `CITATION.cff`. The upstream QASM remains the work of its original authors and is identified by
its Tracker commit, path, retrieval time, and SHA-256 digest.
