# Quantinuum hardware evidence

This directory is a self-contained evidence package for the two problems that
were run on Quantinuum Helios-1 hardware in the `p12_quantum` branch.

| Problem | Hardware job | Requested shots | Reported HQC | Provider timing |
|---|---|---:|---:|---|
| P11 | `c902a6a1-0e91-48cf-b5ba-44831fcc7726` | 50 | 282.98 | 229.924 s execution; 10,732.064 s queue |
| P12 | `d5cba0df-a7aa-459e-ac51-8092645c059f` | 200 | 1,373.4 | 4,160.856 s running-to-completed; 4,580.972 s submitted-to-completed |

The provider timings are not gate-level execution times. P12 also has a nested
result-item runtime of 237.588 s; it is preserved because it differs from the
outer job timestamps. P11 and P12 classical-analysis wall times were not
recorded in the retained telemetry, so they are marked as unavailable in the
per-problem summaries rather than reconstructed or estimated after the fact.

## Package layout

- [`p11/`](p11/) — P11 source, Helios-1 submission/result artifacts, canonical
  shots, analysis, and run documentation.
- [`p12/`](p12/) — P12 source, Helios-1 submission/result artifacts, repaired
  framing record, reconstructed 200-shot dataset, validation, and protocol.

The original artifacts remain in their historical locations elsewhere in the
repository. The files here are organized copies for review and reporting.

## Interpretation boundary

The analyses document candidate recovery and recurrence/structure evidence.
They do not, by themselves, establish a quantum-advantage claim. Any answer
reported from later external scoring is labeled as such in the relevant
summary and is kept distinct from target-blind hardware analysis.
