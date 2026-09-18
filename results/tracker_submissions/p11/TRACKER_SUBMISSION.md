# P11 tracker submission package

## Tracker fields

- Name: `Quantinuum Helios recovery for peaked_circuit_P11_Hqap_98x1999`
- Circuit: `peaked_circuit_P11_Hqap_98x1999`
- Value: `100%`
- Method: `Quantinuum Helios-1 hardware, 50 requested shots`
- Quantum runtime: `229.924343 seconds` of provider execution time
- Quantum queue/submission time: `10732.063968 seconds` (reported separately)
- Classical runtime: `0.005715375 seconds` measured wall time for the packaged reanalysis
- Quantum compute resource: `Quantinuum Helios-1`
- Classical compute resource: `Apple Silicon Mac, local deterministic post-processing`
- Authors: `Monit Sharma`
- Institutions: `Independent researcher`

## Recovered value

```text
10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000
```

The provider result reconstructed to 51 complete records for 50 requested
shots. One record was an exact duplicate: reconstructed index 46 equals index
0 in all 98 bits. The package preserves the raw 51-record reconstruction and
uses the corrected 50-record dataset for active analysis. The saved
canonical-shot audit recovered the accepted string with the weighted
observed-medoid and cluster-consensus procedures; the target was not used by
those procedures.

## Evidence and reproduction

- Source circuit: `quantum/source/P11_hqap_1999.qasm`
- Provider job: `c902a6a1-0e91-48cf-b5ba-44831fcc7726`
- Raw/provider artifacts: `quantum/`
- Canonical shots and analysis: `classical/`
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
from each corrected shot to the recovered candidate. It is descriptive: the
recovered candidate is a medoid rather than a high-frequency observed mode.

The recovery statistics are recurrence/reconstruction evidence only. No
quantum-advantage claim is made in this package.
