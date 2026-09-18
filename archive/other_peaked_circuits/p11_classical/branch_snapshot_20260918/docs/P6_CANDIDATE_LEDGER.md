# P6 candidate ledger

This is the canonical comparison table for P6 bitstring candidates. New
candidates should be appended with their provenance and, when available, the
externally reported overlap. Do not treat similarity to another candidate as
evidence of correctness.

## Evaluated candidates

| ID | Source/provenance | Overlap | Bitstring |
|---|---|---:|---|
| A1 | External evaluated submission | 30/62 | `11100011000101111111011101011001110100110110000011010010010010` |
| A2 | External evaluated submission | 32/62 | `11010000011001111100000010011000110100111101100000111100011010` |
| A3 | External evaluated submission | 35/62 | `10011111010101011010100010111010001100010100101011101001110010` |
| A4 | External evaluated submission | 33/62 | `11001011010111011010100010111011101100110100101111100001110110` |
| A5 | External evaluated submission | 34/62 | `11011011110101011010100010111011001100010100000011100001110010` |
| A6 | External evaluated submission | 35/62 | `10011011110101011010100010111010001100010100100011100001110010` |
| A7 | External evaluated submission | 35/62 | `11011111110101011010100010111010001100010100101011101001110010` |
| A8 | External evaluated submission; previous best | **36/62** | `10011111110101011010100010111010001100010100101011101001110010` |
| D456 | D128 seed 456 candidate, later evaluated | 34/62 | `11111100011101000101100111111010100101110111100100111101110101` |
| C10 | Score-constrained combined-prior candidate | 30/62 | `00011111111100100011100110100000110100110101011000000110110110` |
| C11 | Updated score-constrained combined-prior candidate | **40/62** | `10101111111011011111110000011010110011000101000101101111111000` |
| C12 | Updated score-constrained combined-prior candidate | 30/62 | `00111011101001011000010111111010100011101100001001111011111100` |
| C13 | Score-weighted consensus projected onto all known constraints | 34/62 | `10000100110000011111101001000010100101010100010101101001011100` |

## Unscored candidates

| ID | Source/provenance | Bitstring |
|---|---|---|
| D123 | D128 seed 123 candidate | `11100011000101111010111111011011010100110110010010010010101000` |

These candidates have no externally reported overlap and must not be presented
as validated answers.

## Current record

The best observed result is **C11 at 40/62**. The previous A8 record was
36/62. C10 and C12 demonstrate that satisfying all recorded score constraints
does not imply a high overlap: both were score-consistent hypotheses but scored
only 30/62.

## New-candidate comparison protocol

For every new 62-bit candidate:

1. Verify length and binary alphabet.
2. Compute Hamming distance to every row above.
3. Record whether it is an exact duplicate, a one-bit mutation, or a new
   hypothesis family.
4. If an external score is available, record it in this ledger and update the
   current record only when it exceeds 40/62.
5. Keep score-constrained feasibility separate from predicted overlap; the
   former is a mathematical consistency check, not a correctness estimate.

The machine-readable observations used by the constraint solver are in
`results/p6_oracle_observations.json`; the current constrained ranking is in
`results/p6_constrained_rank.json`.

## Automated pre-submission check

`scripts/p6_verify_candidate.py` turns every scored row above into a hard
constraint on the truth:

```
d(recorded_i, truth) = 62 - overlap_i
```

so any hypothesis `x` must satisfy `d(recorded_i, x) == 62 - overlap_i` for every
row. A single violation **proves** `x` is not the answer.

```bash
python scripts/p6_verify_candidate.py <62-bit-string>
python scripts/p6_verify_candidate.py path/to/summary.json   # reads predicted_bitstring
```

Exit status 0 = consistent, 1 = rejected. The script reads only recorded scores;
it queries nothing.

This is a **necessary, not sufficient** condition -- C10 and C12 satisfied every
constraint and still scored 30/62 (see "Current record"). Passing means "not yet
excluded", never "correct".

Worked example. The best simulated P6 candidate from the MPO route
(`p6main_c2e3_long`, cutoff 2e-3, peak fraction 0.001) violates **13 of 13**
recorded overlaps, most by exactly one bit and two by 5-7. Consistent with a
state that carries no circuit information -- see `P6_MPO_DIAGNOSIS.md` section 9.
