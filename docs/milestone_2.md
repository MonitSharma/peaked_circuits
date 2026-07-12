# Milestone 2: target and output validation

Target discovery is required because historical names, capacities, access rules, and emulator
designations are unstable. The official SDK response is treated as scientific input.

Helios discovery uses authenticated Quantinuum Nexus and `HeliosConfig(system_name=...)`. The legacy
`pytket-quantinuum` device list remains useful for H-series metadata, but it is not evidence of Helios
availability or account access. See [helios_nexus.md](helios_nexus.md).

A plausible 98-bit string in the wrong order is invalid. Compilation requests name preservation and
disables implicit swaps, then checks the actual final map, measurement commands, registers, and output
positions. Requested settings alone are not evidence.

Provider data are preserved raw. Normalization requires an exact mapping from logical qubit through
compiled/provider qubit and classical bit to raw output position. Only canonical `q[0]`-left strings
reach recovery methods.

Six deterministic circuits expose endpoint, reversal, sparse-index, and register-order mistakes.
Until emulator/provider observations for all cases are imported and agree, mapping evidence remains
incomplete.

Smoke-test readiness requires source, target capacity, backend predicates, compiled hash, zero unknown
permutations, complete measurements, mapping cases, synthetic and fixture checks, cost provenance,
frozen protocol, Tracker confirmation, Git provenance, and the hardware guard. Milestone 2 contains no
paid submission implementation and makes no executability claim until validation passes.

Milestone 3 supersedes the Helios transition blocker with local QIR export and a guarded
`Helios-1SC` syntax-check workflow. It does not weaken Milestone 2's provider-order or hardware
safety rules; see [milestone_3.md](milestone_3.md).
