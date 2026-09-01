# Quantinuum hardware-recovery research overview

## Scientific question

Can the hidden peak of the QAT peaked circuits P11 and P12 be recovered from a
small number of noisy samples produced by an all-to-all trapped-ion processor,
with every transformation auditable and without confusing recovery with a
quantum-advantage claim?

## Why Helios is relevant

Both circuits use dense, nonlocal two-qubit interactions. Helios' trapped-ion
connectivity is naturally suited to all-to-all interactions, avoiding the large
nearest-neighbour routing overhead that can obscure a signal on sparse
superconducting-device topologies. This is a hardware-fit argument, not a
claim that the resulting samples are noiseless or that advantage has been
demonstrated.

## Circuit and compilation path

The byte-preserved OpenQASM sources are converted locally to QIR/bitcode using
the repository's pytket/QIR path. Source QASM, submitted artifact, job metadata,
and checksums are retained per problem. The provider job is then linked to the
raw returned result. No source or provider artifact is rewritten in this
package.

## Mapping and bit order

Canonical strings use logical `q[0]` through `q[97]` from left to right. The
mapping layer requires an explicit logical-to-classical layout and rejects
ambiguous order. Deterministic endpoint, sparse, block, and alternating mapping
cases were used before the physical runs; their provenance is linked from the
P12 protocol package. Provider strings are not silently reversed.

## Acquisition and normalization

P11 requested 50 shots and returned 51 complete 98-bit records because the
provider fused the final five frame markers. P12 requested 200 shots; five
fused `END` markers yielded 205 diagnostic cycles, from which five exact
segment-overlap replicas were excluded to reconstruct 200 canonical shots.
The raw payloads remain immutable, and derived shot files identify their raw
parents through manifests and hashes.

## Recovery analysis

The target-blind analysis records mode/multiplicity, Hamming-distance collision
counts, fixed-radius clustering, weighted observed medoid, cluster consensus,
bitwise majority, bootstrap, split-half stability, framing sensitivity, and an
independent rerun where available. Pair counts are descriptive only because
pair events are dependent. P12's most-frequent, weighted-medoid, and
cluster-consensus methods agreed; its coordinate-wise majority differed at 13
positions. P11's 50-shot cluster structure was weak and is not overstated.

## External verification boundary

Later known-answer or tracker scoring is explicitly separated from target-blind
analysis. A reported answer can be externally verified without implying that a
hidden target was used during decoding. The evidence package does not claim a
quantum advantage merely because hardware recovery succeeded.

## Costs and limitations

P11 cost 282.98 HQC. P12 cost 1,373.4 HQC. Provider queue and running times are
reported exactly where retained; they are not gate-level timings. Classical
analysis wall time is not recorded. The small samples, P11 framing discrepancy,
P12 framing anomaly, and noise-sensitive decoder agreement limit what can be
claimed. A complete quantum-advantage case additionally requires a defensible
classical baseline, resource accounting, and the tracker’s evaluation evidence.

See [`HARDWARE_SAFETY.md`](HARDWARE_SAFETY.md),
[`EVIDENCE_LINEAGE.md`](EVIDENCE_LINEAGE.md), and
[`INTERPRETATION.md`](INTERPRETATION.md).
