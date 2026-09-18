# P12 tracker submission package

## Tracker fields

- Name: `Quantinuum Helios recovery for peaked_circuit_P12_Hqap_98x2457`
- Circuit: `peaked_circuit_P12_Hqap_98x2457`
- Value: `100%`
- Method: `Quantinuum Helios-1 hardware, 200 reconstructed shots`
- Quantum runtime: `237.588 seconds` of nested provider execution time
- End-to-end submission-to-completion time: `4580.972377 seconds` (reported separately)
- Outer running-to-completion time: `4160.855590 seconds` (reported separately)
- Classical runtime: `0.010313208 seconds` measured wall time for the packaged reanalysis
- Quantum compute resource: `Quantinuum Helios-1`
- Classical compute resource: `Apple Silicon Mac, local deterministic post-processing`
- Authors: `Monit Sharma`
- Institutions: `Independent researcher`

## Recovered value

```text
10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100
```

The provider response contained five fused `END` markers. The package preserves
the raw response and the deterministic structural repair: 205 framed cycles
were found, five exact segment-overlap replicas were excluded, and 200 shots
were reconstructed. The repaired and reconstructed artifacts are included so
an auditor can inspect this decision rather than relying on a hidden transform.

## Evidence and reproduction

- Source circuit: `quantum/source/peaked_circuit_P12_Hqap_98x2457.qasm`
- Provider job: `d5cba0df-a7aa-459e-ac51-8092645c059f`
- Raw/provider artifacts: `quantum/`
- Raw format note: `quantum/RAW_RESULT_FORMAT.md`
- Reconstructed shots and analysis: `classical/`
- Timing: `timing.md`
- Machine-readable tracker record: `tracker_submission.json`
- Integrity manifest: `SHA256SUMS`
- Diagnostic figure: `figures/frequency_and_distance.png`

The classical runtime was freshly measured with
`tools/run_tracker_classical_audit.py`. It covers shot loading, validation,
count construction, and all four deterministic recovery methods on the stated
Apple Silicon Mac. It does not include Python interpreter startup, plotting, or
provider time.

The figure shows the top-20 observed-string frequencies and Hamming distances
from each shot to the recovered candidate. The candidate is fixed by the
packaged recovery record before plotting; the figure is descriptive supporting
evidence, not a hidden-target lookup.

Mode, weighted observed medoid, and cluster consensus agreed on the recovered
string. Bitwise majority differed at 13 positions. The recovery evidence is
reported separately from any quantum-advantage claim.
