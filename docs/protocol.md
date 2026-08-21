# Draft preregistration protocol

Status: **draft pending confirmation of the evaluation procedure by Tracker maintainers**.

The frozen circuit identity is `peaked_circuit_P12_Hqap_98x2457`; its hash and upstream commit are in
`circuits/original/source_metadata.json`. The intended backend is a currently available, explicitly
configured 98-qubit Quantinuum system. No historical device name is assumed.

The primary method is bitwise majority in canonical logical-qubit order. Secondary methods are most
frequent observed string, weighted observed medoid, and hierarchical cluster consensus. The fresh
provider costing ladder covers 1, 10, 20, 50, 100, 250, 350, 375, 400, 410, 420, 425, 430, 500,
1,000, and 2,000 shots. The recommended future independent batch is 400 shots with a 2,742-HQC
max-cost cap under the 3,000-HQC monthly allocation. Primary endpoint:
percentage of hidden bits recovered. Secondary endpoints: exact match, Hamming distance, bootstrap
stability, and per-bit confidence.

Stop before paid execution if the source hash, compiler snapshot, backend identity, validity predicates,
measurement map, fixture semantics, synthetic tests, cost estimate, Tracker evaluation procedure, or
recovery configuration is unresolved. Failed jobs are retained and reported; no selective exclusion is
allowed except invalid/incomplete provider records documented before target scoring. Compiler or software
version changes require a new manifest and renewed validation. Recovery method changes are exploratory
unless preregistered before target access.

Protocol freeze additionally requires a clean Git commit, an exact discovered target, passing backend
predicates, compiled hash, zero-unknown-permutation measurement mapping, six passing mapping cases,
provider cost provenance, and explicit analysis and shot policies. Tracker rules must be confirmed
before freezing.

The target remains blinded during circuit execution, normalization, candidate selection, and bootstrap
analysis. A frozen candidate and repository commit are sent through the Tracker-confirmed evaluation
route. Target metadata must never be mined to infer the answer.

## Milestone 3 QIR gate

Before any provider mapping experiment, freeze the P12 source hash, export deterministic base-profile
QIR, verify the LLVM module and 98 logical measurement pairs, then syntax-check the six deterministic
mapping cases in their frozen order. P12 may be sent to `Helios-1SC` only after all six pass. A syntax
check is provider-validity evidence, not a measurement-order observation. `Helios-1E` and `Helios-1`
remain outside this protocol.

## Milestone 4 emulator gate

Provider cost-confidence evidence precedes mapping execution. Run the six frozen cases sequentially
with minimal shots, a per-job cap, and the ideal MPS Helios configuration. Preserve labeled raw QIR
records before normalization. Compare each raw layout with that program's declared QIR output-call
order, then normalize labels `m000[0]` through `m097[0]`. A P12 pilot is optional, blinded, and
limited to 20 shots. Physical hardware and hidden-target scoring remain prohibited.

## Future hardware batch plan

The first physical batch remains a future, explicitly authorized action. Use 400 shots and derive
the operational cap from fresh costing (`prediction + 100` HQC, bounded by `3000 - 50` HQC reserve).
For the current 2742-HQC estimate this yields `max_cost=2842` HQC. Preserve each monthly batch independently,
freeze the discovery candidate before confirmation, and analyze cumulative data with batch-aware
bootstrap and leave-one-batch-out checks once at least three batches exist. The fresh syntax and
cost evidence is recorded in `docs/P12_PREHARDWARE_READINESS_AND_COST.md`; no physical execution
was performed while obtaining it.
