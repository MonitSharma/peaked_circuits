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

The raw provider QIR text, job metadata, result reference, backend metadata, submitted input bitcode, manifest, and SHA-256 checksums are preserved under `hardware_campaign/batch_001/provider/`.

## Integrity issue

The downloaded QIR text contains 20,090 labeled `OUTPUT RESULT` records, which equals 205 blocks of 98 outputs. The payload has inconsistent chunk delimiters: 37 ordinary `START`/`END` records followed by five additional chunks without `END` delimiters. Therefore the provider job is complete, but the returned data is not yet accepted as a verifier-clean 200-shot dataset. No canonicalization, recovery analysis, bootstrap analysis, or quantum-advantage claim has been run on this payload.
