# Helios-1 second one-shot smoke test

- Branch: `p12_quantum`
- Target: `Helios-1`
- Requested shots: `1`
- Maximum cost: `80 HQC`
- Provider job name: `p12-physical-smoke-20260825-retry2-125707fb`
- Project: `356d6543-945e-4726-9d0e-a351d87cf859`
- QIR artifact: `41dc61ac-4b14-4aee-9d2a-11aaba66ab60`
- Job: `72109733-fbb2-4a30-984b-312951b366ea`
- Final status: `COMPLETED`
- Final reported cost: `11.84 HQC`
- Result reference: `deb22156-b42b-4971-9096-4ae9d2cf35cb`
- Returned record: 98 bits, 1 shot, 47 ones and 51 zeros

Canonical result order (`m000` through `m097`):

```text
01001001110110101011110111100101001000101011110010100010101001111100010000011000001010110000101011
```

The provider reported `Program has completed` with no error. Backend metadata identifies `Helios-1 Snapshot` with 98 fully connected qubits.

This was a separately authorized diagnostic retry using the same frozen QIR. It is not Batch 001. No retry of this job will be made if the provider again times out; reconciliation will use the deterministic job name.
