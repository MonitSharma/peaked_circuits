# Milestone 4: cost-capped Helios emulator mapping

Milestone 4 completed provider acceptance and output-layout validation without physical hardware.
P12 passed `Helios-1SC`; six deterministic programs then ran sequentially on exact target
`Helios-1E`, using three shots and a `6.0 HQC` ceiling per job. The optional P12 pilot was not run.

## Provenance

The milestone request quoted older pre-provider-compatibility hashes. The authoritative committed
artifacts were regenerated after the Helios gate-compatibility and strict-QIR fixes:

- text QIR: `c003298ea5c57f963f7f9bf5ca4c94a38fc76db10582a5cc859c621ad358c820`;
- submitted bitcode: `c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`.

Both hashes are checked before upload. P12 syntax job
`e49a4854-7f8e-4bc0-80b1-924a593a66d8` completed on `Helios-1SC`.

## Cost and authorization

`nexus-cost` uses `qnexus.qir.cost_confidence`; it does not invent an HQC formula. The API creates a
remote costing job and returns `(estimate, confidence)` tuples, but qnexus 0.46 does not expose that
job reference. Each three-shot mapping estimate was `6.0 HQC` at `95%` confidence. Costing is not
described as free.

Execution also requires `--execute-emulator`, `P12_ENABLE_HELIOS_EMULATOR=1`, authenticated emulator
discovery, prior syntax evidence, matching hashes, a positive `max_cost`, and confirmation. The guard
cannot authorize `Helios-1`, H-series targets, or a syntax checker.

## Helios result structure

Current Helios emulation requires explicit `HeliosEmulatorConfig`. The zero-entanglement mapping
workload uses `MatrixProductStateSimulator`, `NoErrorModel`, and `n_qubits=98`, isolating layout from
fidelity noise.

The optional P12 pilot uses bounded MPS (`backend="auto"`, `chi=128`,
`zero_threshold=0.01`). This follows Quantinuum's documented 100-qubit MPS example and is explicitly
an approximate pipeline check, not an accuracy experiment. Failed jobs retain their job reference,
provider diagnostic, terminal state, reported cost, and simulator configuration.

Nexus returns labeled QIR records grouped by `START`/`END`, such as
`OUTPUT\tRESULT\t0\tm017[0]`. Raw order is program-specific because it follows each QIR program's
`result_record_output` calls. It is deterministic across shots and matched every case's declared
order. Normalization keys on unique labels, never dictionary order. P12's own declared raw order is
recorded, resolving all 98 `provider_result_position` values.

Raw payloads live under `data/provider_raw/mapping`; reports live under
`results/nexus/emulator_mapping`. Every raw payload is hashed. Duplicate or unknown labels,
nonbinary values, wrong widths, shot-varying layouts, QIR-order mismatches, and deterministic-output
mismatches fail validation.

## Evidence limits

Syntax success proves provider acceptance, not execution correctness. Mapping success proves output
normalization, not P12 accuracy or hardware performance. Emulator majority and bootstrap stability
are not Tracker scores. The hidden target remains blinded; physical `Helios-1` is a later milestone.
