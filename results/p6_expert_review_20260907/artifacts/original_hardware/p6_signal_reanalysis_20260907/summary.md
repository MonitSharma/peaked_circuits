# P6 signal reanalysis summary

| run | unique | pairwise min | bits |z|>3 | indep-EM gain | LC-EM gain | LC bootstrap median Δ | vs answer (LC-EM) |
|---|---:|---:|---:|---:|---:|---:|---:|
| null_uniform_500x62 | 500/500 | 15 | 0 | 62 | 29 | 26 | n/a |
| null_independent_bits_with_p6_marginals | 500/500 | 14 | 18 | 241 | 30 | 26 | n/a |
| p11_all_shots | 50/51 | 0 | 33 | 555 | 515 | 0 | 0 |
| p12_all_shots | 198/200 | 0 | 5 | 380 | 369 | 0 | 0 |
| p12_subsample_50 | 50/50 | 19 | 0 | 112 | 80 | 36 | 24 |
| p12_subsample_100 | 98/100 | 0 | 4 | 250 | 223 | 3 | 0 |
| p6_500_corrected | 500/500 | 11 | 17 | 268 | 63 | 10 | n/a |

P6 light-cone EM candidate (majority init): `11101101110100100001000011010101111101001110010101111110100101`
P6 light-cone EM candidate (independent-EM init): `11100100110110100000000011010001111100001110010101111111100001`
Hamming between the two P6 fixed points: 8; split-half (batches 1-3 vs 4-5): 12

Neither P6 string is promoted as a candidate: the decoder is validated on P11/P12 but the P6 optimum is not stable under bootstrap or split-half.
