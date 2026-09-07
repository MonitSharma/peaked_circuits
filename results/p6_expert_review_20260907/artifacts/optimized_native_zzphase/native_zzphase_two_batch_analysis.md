# P6 native-ZZPhase two-batch analysis

The two independent 50-shot runs used identical native-ZZPhase bitcode and were analyzed separately before pooling.

## Batch 1

- Shots analyzed: **50**
- Unique strings: **49**

| Method | Candidate |
|---|---|
| most_frequent | `00001100000010100000110111000100000000101100111100000100010101` |
| bitwise_majority | `01101101110110000000000011010101101100001010001101100100100001` |
| weighted_observed_medoid | `01101101100110010000000011001001111101011000110101111111100001` |
| cluster_consensus | `00001100000010100000110111000100000000101100111100000100010101` |

## Batch 2

- Shots analyzed: **50**
- Unique strings: **49**

| Method | Candidate |
|---|---|
| most_frequent | `00001000110000001010101110001111101101100010000001000010000000` |
| bitwise_majority | `10101100101000000000100111110001111100001011000101100010100000` |
| weighted_observed_medoid | `11000001100000000000100110111101001101001010000101100101110001` |
| cluster_consensus | `00001000110000001010101110001111101101100010000001000010000000` |

## Cross-batch decoder distance

| Method | Hamming distance |
|---|---:|
| most_frequent | 30 |
| bitwise_majority | 17 |
| weighted_observed_medoid | 23 |
| cluster_consensus | 30 |

## Pooled 100-shot summary

- Unique strings: **98**

| Method | Candidate |
|---|---|
| most_frequent | `00001000110000001010101110001111101101100010000001000010000000` |
| bitwise_majority | `11101100100110000000100011010101111100001010000101100110100001` |
| weighted_observed_medoid | `11101000110010100000000111100111111100010110000101111111110001` |
| cluster_consensus | `00001000110000001010101110001111101101100010000001000010000000` |

The pooled result is exploratory only and remains separate from the earlier 500-shot campaign.
