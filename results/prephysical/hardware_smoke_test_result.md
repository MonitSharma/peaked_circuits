# Helios-1 smoke-test result

- Branch: `p12_quantum`
- Target: `Helios-1`
- Job reference: `62dd05e1-9d5b-48dc-be28-b5a41d45df21`
- Result reference: `d274eef6-1bcd-4e23-a075-6e55f910a316`
- Requested/returned shots: `1 / 1`
- Provider-reported cost: `11.84 HQC`
- Input QIR artifact: `b906176d-7d0e-4528-b39d-fac72d9df604`
- Backend metadata: `Helios-1 Snapshot`, 98 qubits, fully connected

## Provider status

Nexus exposes a result payload, but the result status also reports a provider submission error:
`Submission error: Job ID ('id') already exists. (code: 102)`.
There is no running timestamp. Treat this as a provider-side metadata/submission anomaly, not as a clean hardware success.

## Returned QIR record

The returned payload is one labeled 98-bit record. Canonical order below is `m000` through `m097`:

```text
10100101101000010100010001011101001010010101010011001110011001111110000111110110101001011000001101
```

It contains 48 ones and 50 zeros. Ones are at:
`m000,m002,m005,m007,m008,m010,m015,m017,m021,m025,m027,m028,m029,m031,m034,m036,m039,m041,m043,m045,m048,m049,m052,m053,m054,m057,m058,m061,m062,m063,m064,m065,m066,m071,m072,m073,m074,m075,m077,m078,m080,m082,m085,m087,m088,m094,m095,m097`.

Batch 001 was not submitted or modified.
