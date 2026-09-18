# Local-unitary patch invariants for U/U-dagger recovery — closed by degeneracy

**Verdict: closed.** The invariant discriminates on P5 but is degenerate on P6,
P8 and **P9** -- and P9 is the mandatory positive control, the one circuit whose
hidden cancellation is known to be recoverable. The route cannot be validated
where it would have to be.

## The idea being tested

The HQAP construction is `T[R] > T[U] > U^dag > P`, where `T` applies coordinated
swaps, angle sweeping and masking. Earlier scans looked for a single global
permutation and found nothing (fixed mapping matched 0 edges at widths 16-256).
The generator says the relevant object is a **time-dependent** permutation
`pi(t)`, so a fixed mapping was testing the wrong hypothesis.

The proposed fix: a Viterbi/beam decoder over permutation states, using
local-unitary invariants of two-qubit patches as emission probabilities --
because angle sweeping was designed to defeat raw angle comparison, while
Weyl/Cartan coordinates are invariant under the local resynthesis that sweeping
and masking perform.

Before building that decoder, this screens its necessary condition: a permutation
relabels *where* patches sit, not *which* patches exist, so the multiset of patch
invariants must match across the `T[U] | U^dag` boundary.

## Why it fails

`scripts/patch_invariant_screen.py`, with `results/patch_invariants/weyl_degeneracy.json`:

| circuit | maximal 2q patches | entanglers/patch (mode) | distinct Weyl coords (of 800) | modal fraction |
|---|---:|---:|---:|---:|
| P5 | 902 | 2 | **792** | 0% |
| P8 | 808 | 1 | 77 | 90% |
| **P6** | 2593 | 1 (1865 of 2593) | 137 | **72%** |
| **P9** | 1885 | 1 (1853 of 1885) | **16** | **98%** |

**CZ has fixed Weyl coordinates `(pi/4, 0, 0)`, and local rotations cannot change
them** -- that is precisely what makes them local-unitary invariants. When a
maximal patch contains exactly one entangler, its coordinates are that constant.
P6 has 1865 single-entangler patches of 2593; P9 has 1853 of 1885.

P5 is the exception because it averages 2.1 CZ per patch (1892 CZ / 902 patches),
so its patches carry genuinely varying invariants.

## The structural reason the idea cannot work as specified

The two halves of the motivating argument defeat each other:

* angle sweeping defeats raw angle comparison;
* local-unitary invariants defeat angle sweeping -- **by discarding the angles**.

For a circuit whose only entangler is CZ, what survives that discard is a
constant. So the decoder's emission probabilities are uniform over 72% of P6's
patches and 98% of P9's, and the beam search degenerates into a random walk over
permutations.

This also retroactively explains the earlier KAK result. "Fixed mapping matched 0
edges" was not a failure of the *fixed* assumption -- there was nothing to match
on.

## Why the control failure is decisive

P9's hidden cancellation is known to be classically recoverable; the
Kremer/Dupuis unswapper exploits exactly that mechanism. If a fingerprinting
method cannot discriminate patches on P9, it cannot be validated, and an
unvalidated decoder run on P6 would produce a permutation trajectory with no way
to tell signal from noise.

## What would be needed instead

* **Multi-entangler patches only.** P6 has 555 two-CZ and 173 three-CZ patches
  with genuinely varying coordinates -- but that is ~28% of patches, and P9 has
  32 of 1885, so the control still fails.
* **Larger 3-4 qubit patches** with richer invariants. More expensive, and
  masking is explicitly permitted to replace local structure, so survival is not
  assured.

Neither justifies building the sequential decoder, and the second has no working
positive control.

## Implementation note

The screen's boundary sweep returned distance 0.0000 at every boundary on both a
planted `U > U^dag` control and a random circuit -- not a bug, but the degeneracy
itself: the clouds are identical because every patch is the same point. Weyl
invariance under local rotations was verified separately (5/5 random cases to
1e-6), so the coordinate computation is correct.

## Artifacts

`scripts/patch_invariant_screen.py`, `results/patch_invariants/weyl_degeneracy.json`.
