# P1 — classical campaign

**Outcome:** `METHOD_EXHAUSTED`

## Problem

P1 is the 36-qubit peaked circuit used for the early classical and provider
experiments. The v2 audit records 1,457 two-qubit gates, depth 307, and a
two-qubit depth of 153. The canonical source hash is
`0a02afffbdcf6755d5ed16b3a10cddd40cde4ee072d6072dbe7013e1c42f2ff8`.

## Scientific objective

Recover the circuit's peaked output without using hidden answer information,
then distinguish a genuine peak from a simulator or readout artifact. A useful
result requires provenance, a reproducible circuit, and fidelity evidence—not
just a high-scoring individual sample.

## Headline result

| Evidence | Result | Interpretation |
|---|---|---|
| BlueQubit v1/v2 audits | retained provider/classical evidence | diagnostic, not a verified blind solution |
| Classical methods | no promoted exact candidate recorded | method families exhausted within tested resources |

## Methods attempted

| Method family | Outcome | Evidence |
|---|---|---|
| BlueQubit/provider submissions | diagnostic artifacts retained | [`BLUEQUBIT_P1_V2_AUDIT.md`](../../docs/BLUEQUBIT_P1_V2_AUDIT.md) |
| tensor-network and structural probes | no verified promotion | [`ARTIFACTS.md`](ARTIFACTS.md) |

## Canonical artifacts and reproduction

Start with [`ARTIFACTS.md`](ARTIFACTS.md), the v2 audit, and the source QASM
listed there. Provider or hardware runs are not routine reproduction targets.

## Limitations

This page does not claim mathematical impossibility or a verified target. Some
historical P1 material predates the current validation protocol.
