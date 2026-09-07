# P6/P8 Helios cost estimates

Fresh provider cost-confidence estimates were obtained for the prepared,
explicitly measured QIR artifacts. No emulator or hardware execution was
submitted.

`Helios-1SC` is a syntax-check target and does not return HQC pricing. The
prices below come from the separate Helios cost-confidence endpoint, using
`Helios-1` as the costing system. Every estimate reported 95% confidence.

| Circuit | 50 shots | 200 shots |
|---|---:|---:|
| P6 | **431 HQC** | **1,708 HQC** |
| P8 | **259 HQC** | **1,018 HQC** |

These are execution-cost estimates, not recovery guarantees. The weighted
medoid/cluster-consensus procedure that worked for the P11/P12 observations
only helps select a candidate when the returned shots contain a repeatable
cluster. It does not reduce HQC cost or recover a signal destroyed by routing
and hardware noise. P8 is the cheaper option, but its previous 5-shot Helios
run and 1,000/8,000-shot IBM runs were diffuse and should be treated as prior
diagnostic evidence when deciding whether to spend more.
