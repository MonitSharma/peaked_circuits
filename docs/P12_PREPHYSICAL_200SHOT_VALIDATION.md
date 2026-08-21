# P12 pre-physical 200-shot validation

## Verdict

**BLOCKED_PREPHYSICAL**. The required local correction is committed at `e4b6f9eccf79634dea23ea5b0bfe5ebc58c11665`, but the goal requires provider calls only when local HEAD equals the fetched remote branch. The corrected commit is one commit ahead of `origin/p12_quantum`; repository instructions do not authorize pushing. Therefore no provider costing or emulator pilot was run.

## Git synchronization

- Remote: `https://github.com/MonitSharma/p12-helios-recovery.git`
- Branch: `p12_quantum`
- Starting/local fetched SHA: `5b75ec288dace7a64c85523bb9f448e7e7f6d910`
- Final local SHA: `e4b6f9eccf79634dea23ea5b0bfe5ebc58c11665`
- Fetched remote SHA: `5b75ec288dace7a64c85523bb9f448e7e7f6d910`
- Final tree: clean
- Initial synchronization: matched exactly
- Final synchronization: local ahead by one intended commit; provider gate not satisfied

## Frozen identity

- QASM SHA-256: `868ff86a396f86a8cbca48f7127e49c4c4f951a5a955295e5010a92b76be961d`
- QIR text SHA-256: `c003298ea5c57f963f7f9bf5ca4c94a38fc76db10582a5cc859c621ad358c820`
- QIR bitcode SHA-256: `c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`
- Width: 98 logical qubits and 98 measured outputs
- Mapping evidence: existing 98-position mapping evidence retained

## Physical campaign changes

Batch 001 remains `PLANNED`, discovery role, exact target `Helios-1`, exactly 200 shots, with a user spend ceiling of 1500 HQC. Monthly allocation remains 3000 HQC. The protocol hash was recomputed as `d88ea05069834adad820c75046022a678cda2a43ba9944ebf6793133a41898c5`.

## Local validation

- `pytest -q -m "not hardware"`: 127 passed
- `ruff check .`: passed
- `mypy src`: passed
- `python -m p12_recovery.cli schemas --check`: passed
- Authenticated discovery: passed for Helios-1SC, Helios-1E, and Helios-1
- Fresh 200-shot HQC estimate: not requested because the clean local==remote provider gate was not satisfied
- 3-shot Helios-1E cost estimate: not requested
- 200-shot physical dry run: not run because it requires provider-backed current evidence
- Helios-1E pilot: not run

Existing historical emulator evidence was not treated as this goal’s pilot; no hidden target was accessed or scored.

## Safety accounting

Helios-1 physical jobs submitted: 0  
Helios-1 physical shots executed: 0  
Physical HQCs spent: 0  
Helios-1E P12 pipeline-test jobs submitted: 0  
Helios-1E P12 pipeline-test shots requested: 0

To continue, the corrected commit must be synchronized with the authoritative remote branch under an explicitly authorized workflow, after which fresh provider evidence must be obtained. Do not proceed to Helios-1 without separate user GO/NO-GO approval.
