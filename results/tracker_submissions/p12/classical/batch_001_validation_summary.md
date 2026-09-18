# Batch 001 internal validation checks

These checks are target-blind and use no additional HQC. They operate on the reconstructed 200-shot dataset and do not replace an independent hardware confirmation batch.

## Results

- Split-half candidates (100 shots vs 100 shots): Hamming distance **31**.
- First-half candidate vs full candidate: Hamming distance **12**.
- Second-half candidate vs full candidate: Hamming distance **19**.
- Random subsampling match probability with the full candidate:
  - 50 shots: `0/200`
  - 100 shots: `0/200`
  - 150 shots: `0/200`
  - 200 shots: `200/200` (the full sample is always selected)
- Framing sensitivity: raw 205-cycle majority differs from reconstructed 200-shot majority by **2 bits**.
- Independent rerun from reconstructed JSONL: exact counts and candidate match the stored artifacts.
- At a nominal per-bit 95% margin threshold, the observed data have 28 bits above threshold versus a mean of 5.465 in 200 fair-random simulations. This indicates aggregate bit bias, but it is not by itself evidence of a recoverable answer.

## Interpretation

The data show non-random per-bit structure, but the candidate is not stable under split-half or subsampling analysis. The reconstructed candidate should therefore remain a frozen discovery hypothesis, not a validated answer or quantum-advantage result. A fresh, independent confirmation batch is still required.
