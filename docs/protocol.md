# Draft preregistration protocol

Status: **draft pending confirmation of the evaluation procedure by Tracker maintainers**.

The frozen circuit identity is `peaked_circuit_P12_Hqap_98x2457`; its hash and upstream commit are in
`circuits/original/source_metadata.json`. The intended backend is a currently available, explicitly
configured 98-qubit Quantinuum system. No historical device name is assumed.

The primary method is bitwise majority in canonical logical-qubit order. Secondary methods are most
frequent observed string, weighted observed medoid, and hierarchical cluster consensus. Planned shot
ladder: 10, 20, 50, 100, 250, 500, 1,000, 2,000, subject to approved cost and access. Primary endpoint:
percentage of hidden bits recovered. Secondary endpoints: exact match, Hamming distance, bootstrap
stability, and per-bit confidence.

Stop before paid execution if the source hash, compiler snapshot, backend identity, validity predicates,
measurement map, fixture semantics, synthetic tests, cost estimate, Tracker evaluation procedure, or
recovery configuration is unresolved. Failed jobs are retained and reported; no selective exclusion is
allowed except invalid/incomplete provider records documented before target scoring. Compiler or software
version changes require a new manifest and renewed validation. Recovery method changes are exploratory
unless preregistered before target access.

The target remains blinded during circuit execution, normalization, candidate selection, and bootstrap
analysis. A frozen candidate and repository commit are sent through the Tracker-confirmed evaluation
route. Target metadata must never be mined to infer the answer.

