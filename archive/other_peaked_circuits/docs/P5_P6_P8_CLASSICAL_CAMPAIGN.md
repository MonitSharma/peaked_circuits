# P5/P6/P8 classical-only campaign

Status: classical exploration completed for this pass; no emulator or real
hardware jobs were submitted.

The source package was reviewed from
`<local-user>/Code/p12-helios-recovery/results/expert_review_p5_p6_p8_20260828/`.
The latest online `p11_classical` branch was also checked at commit
`1ff7a975347fdef43c9b1f2ae04df36d9812ba42`. The branch contains substantial
P9/P11 work and the supplied expert-review package, but no externally verified
P5, P6, or P8 answer.

## Held-out tracker evaluations

These scores were supplied after the original classical candidates were
generated. They are recorded as evaluation results only and were not used to
tune the new classical runs:

| Problem | Original candidate | Tracker overlap |
|---|---|---:|
| P5 | `00010110000100100101100011011101110010110011` | 30/44 |
| P6 | `11011011110101011010100010111011001100010100000011100001110010` | 34/62 |
| P8 | `0010111110100001101010111000001111111011` | 24/40 |

An overlap score is not a bit-level correction signal. It must not be fed back
into candidate generation or used to adaptively guess individual bits.

## Independent CircuitPermMPS checks

The same D=128, cutoff `1e-12`, 1,000-sample CircuitPermMPS procedure was run
with a new seed (`789`) against each supplied QASM. The output is a voted
marginal candidate; all three new runs had zero observed occurrences of their
voted candidate, so the runner classified them as weak unless repeated.

| Problem | New candidate (seed 789) | Runtime | Result |
|---|---|---:|---|
| P5 | `10111101000001111100100110011101010000101001` | 183.8 s | weak/diffuse |
| P6 | `10001000011000101110100011011010110011010011111000100100011000` | 640.4 s | weak/diffuse |
| P8 | `1000100010111001111101001011111010010011` | 59.0 s | weak/diffuse |

The new P5 and P6 candidates differ from the earlier MettleQ candidates by 17
and 33 bits respectively. The new P8 candidate differs by 5–6 bits from the
two prior CircuitPermMPS seeds, which themselves differed by 5 bits.

## Scientific decision

- **P5:** not promoted. The original MettleQ candidate had 5 split-half
  disagreements and the independent D=128 run did not reproduce it.
- **P6:** not promoted. Although the original MettleQ run had zero split-half
  disagreements and 62/62 bootstrap-stable bits, the independent D=128 run
  produced a candidate 33 bits away. Internal stability was therefore not
  cross-method correctness.
- **P8:** not promoted. MettleQ, three CircuitPermMPS seeds, PEPS, and the
  bounded PEPO probe do not provide a stable independent candidate. The PEPO
  probe also produced an invalid probability and is numerical-failure evidence
  only.

The result is **no classical candidate ready for hardware verification**.
The appropriate next action is to stop this pass, preserve the artifacts, and
only resume if a new independent algorithm or a validated ordering/semantics
fix is available. No hardware or emulator execution was authorized or
performed in this campaign.
