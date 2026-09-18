# Batch 001 retrieval status

- Job name: `p12_physical_sqd`
- Job ID: `d5cba0df-a7aa-459e-ac51-8092645c059f`
- Result reference: `2e7cee36-577a-48d2-a848-ed1e7848b3fc`
- Provider status: `COMPLETED`
- Provider message: `Program has completed`
- Requested shots: `200`
- Provider-reported cost: `1373.4 HQC`
- Running time: `2026-08-25T11:47:09Z`
- Completion time: `2026-08-25T12:56:30Z`

## Evidence preserved

The raw provider QIR text, job metadata, result reference, backend metadata, submitted QIR reference, actual submitted input bitcode, manifest, and SHA-256 checksums are preserved under `hardware_campaign/batch_001/provider/`. The actual submitted bitcode hashes to `c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`, matching the frozen `results/qir/p12.bc`.

## Integrity issue

The downloaded QIR text contains 20,090 labeled `OUTPUT RESULT` records, forming 205 fixed-width 98-record diagnostic cycles. Five `END` markers are fused directly onto the final `OUTPUT` line of a cycle, and the payload has 42 `START` markers but only 37 standalone `END` markers. Therefore the provider job is complete, but the returned data is not yet accepted as a verifier-clean 200-shot dataset. No canonicalization, recovery analysis, bootstrap analysis, or quantum-advantage claim has been run on this payload.
