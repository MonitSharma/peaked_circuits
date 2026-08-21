# Nexus provider cost evidence

`qnexus.qir.cost_confidence` creates a remote costing job. It is not described as free; the returned API value contains estimates and confidence but no job reference.

The costing system was `Helios-1`; no execution API was called. Under the 3,000-HQC monthly
allocation, the largest tested point that fits is 430 shots at 2,948 HQC. The recommended
future batch is 400 shots with a fresh prediction of 2742 HQC. The operational cap is derived
at runtime as prediction + 100 HQC allowance, bounded by the 3000-HQC budget less a 50-HQC reserve;
for this estimate it is `max_cost=2842` HQC.

| Program | Shots | Estimated HQC | Confidence |
|---|---:|---:|---:|
| p12 | 1 | 12.0 | 95.0 |
| p12 | 10 | 74.0 | 95.0 |
| p12 | 20 | 142.0 | 95.0 |
| p12 | 50 | 348.0 | 95.0 |
| p12 | 100 | 690.0 | 95.0 |
| p12 | 250 | 1716.0 | 95.0 |
| p12 | 350 | 2400.0 | 95.0 |
| p12 | 375 | 2571.0 | 95.0 |
| p12 | 400 | 2742.0 | 95.0 |
| p12 | 410 | 2811.0 | 95.0 |
| p12 | 420 | 2879.0 | 95.0 |
| p12 | 425 | 2913.0 | 95.0 |
| p12 | 430 | 2948.0 | 95.0 |
| p12 | 500 | 3427.0 | 95.0 |
| p12 | 1000 | 6848.0 | 95.0 |
| p12 | 2000 | 13690.0 | 95.0 |
