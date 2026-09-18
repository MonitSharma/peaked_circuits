# P11 blind extraction protocol

## Status and scope

This protocol is preregistered before the new cross-run extraction statistics.
It uses only the two existing completed, blind P11 sample datasets. It does
not search for, import, or compare against an external P11 target.

The question is whether the approximate states preserve reproducible
bitwise information despite diffuse full-string sampling.

- H0: the two approximate states contain no reproducible latent 98-bit center.
- H1: the two approximation levels preserve reproducible bitwise structure.

The fixed approximation levels are cutoff `5e-3` and cutoff `4e-3`, both with
max bond `4096`, the validated routing configuration, and 1,000 blind shots.

## Required metrics

For each run, calculate:

1. `p_i(1)`, `p_i(0)`, absolute bias, per-bit binary entropy, and Wilson 95%
   intervals for all 98 canonical output positions.
2. A deterministic bitwise-majority candidate. Exact ties are recorded as
   uncertain and resolved only by the preregistered tie rule: choose `0` for
   a machine-readable candidate while retaining an uncertainty flag.
3. At least 2,000 deterministic-seed bootstrap replicates over shots, including
   per-bit majority-sign stability and whole-candidate Hamming distance to the
   full-run majority.
4. Repeated random subsampling at sizes 50, 100, 200, 400, 600, and 800,
   measuring candidate Hamming distance and agreement with the full-run
   majority.
5. Within-run pairwise Hamming-distance summaries using a streaming calculation.
6. Cross-run majority-candidate Hamming distance and per-bit sign agreement.
7. Held-out cross-run Hamming-distance tests in both directions. The candidate
   is derived from one run only and every sample in the other run is scored.
   Report mean, median, standard deviation, quantiles, effect size relative to
   the random-null mean 49, and a 2,000-replicate bootstrap 95% CI for the mean.

## Fixed decision gates

For 98 unbiased bits, the null reference is Binomial(98, 0.5), with mean 49
and standard deviation approximately 4.95. The empirical bootstrap is the
primary uncertainty estimate.

`STRONG_CROSS_RUN_SIGNAL` requires all of:

- majority candidates differ by at most 12 bits;
- at least 80 of 98 majority signs agree;
- in both held-out directions, the bootstrap 95% CI for mean Hamming distance
  lies strictly below 48;
- at least 60 positions have bootstrap majority-sign stability at least 0.90
  in both runs.

`MODERATE_CROSS_RUN_SIGNAL` requires all of:

- majority candidates differ by at most 20 bits;
- at least 70 of 98 majority signs agree;
- both held-out mean Hamming distances are statistically below 49 under the
  preregistered bootstrap test.

Otherwise report `NO_REPRODUCIBLE_SIGNAL` when majority agreement is near
random, held-out distances are compatible with 49, and marginal signs are not
bootstrap-stable. Phase A does not by itself terminate the project if the
implementation and input data are valid.

## Reproducibility

- Bootstrap RNG: NumPy PCG64, seed `20260827`.
- Subsampling RNG: NumPy PCG64, seed `20260828`, independent per run and size.
- Quantiles: NumPy linear interpolation (`method="linear"`).
- Hamming distance: number of unequal canonical bits.
- Candidate terminology: `BLIND_MAJORITY_CANDIDATE`; no result is called a
  P11 answer or verified solution.

## Immutable inputs and outputs

The original sample files are read-only evidence and are never overwritten.
New analysis outputs go under:

`results/p11_extraction/existing_samples/`

Required files are `analysis.json`, `per_bit.csv`, `cross_run.json`,
`bootstrap.json`, and `SHA256SUMS`.
