# MettleQ patch provenance

The native lookahead probe exposed a stale-layout bug: the persistent planner
assumed identity layout even when the MPS distiller initialized a Fiedler layout.
The targeted patch is stored at
`hpc/solver_patches/mettleq_initial_layout.patch`.

It passes the actual `site_to_logical` permutation into the portable planner,
validates it, and keeps the optional native planner for identity-layout calls.
The patch is not part of the frozen P9/P11 solver path.

External checkout: `/Users/monitsharma/code_projects/Qupertino`.
Base checkout commit: `a850c793c011ac21cb4ef9ac1db75eb381e6852e`.
The checkout had unrelated pre-existing local modifications; only the two
targeted changes above are attributed to this P1 experiment.
