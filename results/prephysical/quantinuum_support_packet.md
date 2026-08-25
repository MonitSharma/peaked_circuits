# Quantinuum result-framing support packet

Please investigate this completed Nexus result without changing or rerunning the job.

- Target: `Helios-1`
- Job name: `p12_physical_sqd`
- Job ID: `d5cba0df-a7aa-459e-ac51-8092645c059f`
- Result reference: `2e7cee36-577a-48d2-a848-ed1e7848b3fc`
- Requested shots: `200`
- Provider-reported cost: `1373.4 HQC`
- Result status: `COMPLETED`, `Program has completed`
- Frozen submitted bitcode SHA-256: `c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`

The downloaded labeled QIR payload contains 20,090 `OUTPUT RESULT` records, equivalent to 205 fixed-width 98-record cycles. Five `END` markers are fused directly onto final `OUTPUT` lines. The payload has 42 `START` markers, only 37 standalone `END` markers, and repeated headers/chunk boundaries. The current raw payload and all hashes are preserved in `hardware_campaign/batch_001/provider/`.

Questions:

1. Is this a known Nexus QIR result serialization or pagination/reassembly behavior for this job type?
2. What are the authoritative boundaries for the requested 200 physical shots?
3. Can you provide a corrected or re-exported result payload, or confirm how to reconstruct the exact 200 shots without selecting records post hoc?
4. Does the saved result reference expose an authoritative shot count distinct from the malformed textual framing?

The actual submitted QIR was retrieved through the returned `QIRRef.download_qir()` and its SHA-256 matches the frozen bitcode exactly. No canonicalization, target decoding, scoring, or quantum-advantage analysis has been performed.
