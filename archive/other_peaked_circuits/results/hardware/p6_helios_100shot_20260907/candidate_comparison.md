# P6 discovery candidate comparison

The hardware candidate was frozen from target-blind analysis before this
comparison. Existing overlap scores are post-hoc context only.

## Hardware candidate

`01001001111111011000101110111001110111101110010011000011111101`

Most-frequent and cluster-consensus agreed exactly. The candidate appeared
4 times in the reported first 100 reconstructed frames.

## Comparison with existing P6 hypotheses

| Existing hypothesis | Previously reported overlap | Hamming distance from hardware candidate |
|---|---:|---:|
| Original MettleQ candidate | 34/62 | 25/62 |
| CircuitPermMPS D=128 seed 789 | not verified; weak/diffuse | 34/62 |
| Best score-constrained hypothesis | 40/62 | 29/62 |

The overlap values are scores of the older hypotheses against the hidden answer;
they are not scores of the new hardware candidate. They were not used to select
or modify the hardware candidate.
