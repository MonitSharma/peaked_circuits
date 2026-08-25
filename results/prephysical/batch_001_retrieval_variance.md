# Batch 001 retrieval variance

The completed Nexus job was retrieved again without execution or HQC spend:

- Job ID: `d5cba0df-a7aa-459e-ac51-8092645c059f`
- Result reference: `2e7cee36-577a-48d2-a848-ed1e7848b3fc`
- Provider status: `COMPLETED`
- Final cost: `1373.4 HQC`

This retrieval returned the same payload as the preserved copy:

- Payload SHA-256: `c45634e68b839e18e3eef0748aac99d8da02e515449053056cb4677e4335ac82`
- Labeled output records: `20090`
- `START` markers: `42`
- `END` markers: `37`

A prior strict parser counted 20,085 records because it rejected five lines where `END` was fused directly onto the final `OUTPUT` line. The raw payload itself is consistently 20,090 records; the job and result references were unchanged.
