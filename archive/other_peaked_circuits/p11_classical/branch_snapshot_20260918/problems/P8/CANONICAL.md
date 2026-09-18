# P8 — solved by tail materialization

**Outcome:** `SOLVED_CLASSICAL`

## Problem

P8 is the 40-qubit grid circuit with 888 native iSWAP gates and 1,816 U3
gates, consolidated to 808 work gates. Source hash:
`ba42c338478fdfbc0241ec2289b3159bfde5dffc71603ac588ec0755fba1a484`.

## Scientific objective

Recover the exact 40-bit peak with a blind classical simulation and validate it
independently. The criterion is not merely reaching a high gate count: the
final distribution must retain a separated peak and the candidate must be
frozen before external evaluation.

## Headline result

| Route | Progress | Readout |
|---|---:|---|
| ordinary/balanced/beam controllers | 799–804/808 | terminal attractors |
| tail materialization from 804/808 | residual 4 gates applied | 38/1000, 3.8%; top1/top2 6.44× |
| external validation | complete | 40/40 |

Candidate: `1000011001010101101111011100000111000111`.

## Methods and why they mattered

The permutation-frame, balance, tabu, and beam experiments localized the
attractor. `flip_freq=2` reached 804/808. The successful change was to
materialize the live MPO and residual layers when only four work gates remained,
rather than forcing the unswap controller to finish.

## Canonical artifacts and reproduction

See [`P8_TAIL804_CANDIDATE.md`](../../docs/P8_TAIL804_CANDIDATE.md),
[`P8_804_FORENSIC_RECONSTRUCTION.md`](../../docs/P8_804_FORENSIC_RECONSTRUCTION.md),
and [`ARTIFACTS.md`](ARTIFACTS.md). The candidate freeze precedes evaluation.

## Limitations

The result validates this recorded checkpoint and handoff path. It does not
claim that every seed or controller reaches 804/808.
