# Milestone 3: QIR and Helios syntax validation

## Why QIR

Quantinuum Nexus supports QIR programs on Helios, and `pytket-qir` is the official one-way converter
for pytket circuits. Helios is therefore not routed through the retired H-series submission
interface. This repository uses:

```text
pytket.qir.conversion.api.pytket_to_qir
QIRFormat.STRING
QIRProfile.BASE
```

The frozen P12 source contains `U3` and `CZ`. An explicit, recorded local rebase converts `U3` into
supported `Rz` and `PhasedX` operations while preserving `CZ`. No placement or routing pass is used,
and implicit wire swaps are rejected.

Official references:

- [pytket-qir API](https://docs.quantinuum.com/tket/extensions/pytket-qir/api.html)
- [Pytket to QIR in Nexus](https://docs.quantinuum.com/nexus/trainings/notebooks/basics/qir/pytket_to_qir.html)
- [Nexus QIR API](https://docs.quantinuum.com/nexus/nexus_api/qir.html)
- [Quantinuum syntax checkers](https://docs.quantinuum.com/systems/user_guide/hardware_user_guide/access.html)

## The 98-output contract

`pytket-qir` 2.0 rejects a classical register wider than 64 bits. P12 therefore uses 98 explicitly
named one-bit registers, `m000[0]` through `m097[0]`. Local validation parses every QIR measurement
call and requires the exact set `(qir_qubit_index, qir_result_index) = (i, i)` for `i=0..97`.

The QIR mapping records canonical position `i` for logical `q[i]`. It never fills
`provider_result_position`; only later emulator observations can establish that field.

## Evidence limits

LLVM parsing, module verification, resource counting, operation accounting, and deterministic
fixture conversion are structural evidence. No local QIR execution engine is installed, so this
milestone does not claim executable semantic equivalence for P12. The six mapping patterns are
syntax-checked first because endpoint, sparse, block, and alternating patterns make reversal errors
observable in a later emulator milestone.

## Syntax-check boundary

The optional remote operation is fixed to `Helios-1SC`, which is a syntax checker. `Helios-1E` is an
emulator and `Helios-1` is hardware; both are refused. Authorization requires:

1. `--submit-syntax-check`;
2. `P12_ENABLE_NEXUS_SYNTAX_CHECK=1`;
3. authenticated discovery of exact `Helios-1SC` as `syntax_checker`;
4. validated QIR and matching text/bitcode hashes;
5. matching Git/artifact provenance;
6. all six mapping syntax checks before P12;
7. interactive confirmation.

The workflow uploads LLVM bitcode through `qnexus.qir.upload` and creates a Nexus job configured only
with `qnexus.models.HeliosConfig(system_name="Helios-1SC")`. The schema permits `max_cost=None` for
syntax-checker names ending in `SC`; the repository does not invent a cost ceiling. Syntax checking
uses no hardware HQCs and stores only sanitized project, artifact, and job identifiers.

## Readiness ceiling

Local completion reaches `READY_FOR_SYNTAX_CHECK`. Successful mapping and P12 syntax checks can reach
`READY_FOR_EMULATOR_MAPPING_VALIDATION`. Milestone 3 has no hardware readiness state. Provider output
order and emulator mapping validation remain deliberately false.
