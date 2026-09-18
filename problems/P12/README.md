# P12 — hardware recovery record

## Status

`SOLVED_HARDWARE`: the recovered 98-bit answer was externally accepted. This
is a recovery result, not a standalone quantum-advantage claim.

## Circuit

`peaked_circuit_P12_Hqap_98x2457`: 98 qubits and 2,457 CZ gates. The source is
the repository byte-preserved QASM at
`circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm`. SHA-256:
`868ff86a396f86a8cbca48f7127e49c4c4f951a5a955295e5010a92b76be961d`.

## Hardware run

Quantinuum Helios-1 job `d5cba0df-a7aa-459e-ac51-8092645c059f` requested 200
shots and cost 1,373.4 HQC. The submitted bitcode SHA-256 is
`c6996dfba55a45549b5c8d3017797f4b561f0af58e7610e5ba3fac8882ae371d`.
Provider timing is 4,580.972377 s submitted-to-completed and 4,160.855590 s
outer running-to-completed; a nested result item reports 237.588 s.

## Target-blind analysis and recovery

Five fused `END` markers produced 205 diagnostic cycles. The structural
reconstruction excluded five exact segment-overlap replicas and yielded exactly
200 canonical shots. Most-frequent, weighted observed medoid, and cluster
consensus agreed; coordinate-wise majority differed at 13 positions. Pair
counts remain descriptive only. Split-half, bootstrap, framing-sensitivity, and
independent-rerun checks are retained.

## External verification

The final answer and external-verification boundary are documented in
[`results/quantinuum/p12/solution_summary.md`](../../results/quantinuum/p12/solution_summary.md).
The normalized project status is `SOLVED_HARDWARE`; it is not a
quantum-advantage claim.

## Evidence and reproduction

Start at the [P12 tracker package](../../results/tracker_submissions/p12/) and
its [package README](../../results/tracker_submissions/p12/TRACKER_SUBMISSION.md).
The complete raw provider framing, repaired artifact, reconstruction manifest,
canonical shots, counts, and analyses are available offline.
