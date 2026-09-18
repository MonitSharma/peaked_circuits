# BlueQubit P1 HPC preparation policy

No HPC job is authorized by the current Mac screening state. The machine-readable
manifest at `results/bluequbit_p1/HPC_MANIFEST.jsonl` contains no executable
configuration because no P1 method has passed the Mac evidence gate.

When a configuration does pass, use a separate `results/bluequbit_p1` namespace
and retain the existing `hpc/run_numa_job.sh`, preflight, and resumable-campaign
infrastructure. Do not modify the P11 campaign launcher.

Each future entry must record the P1 SHA256
`0a02afffbdcf6755d5ed16b3a10cddd40cde4ee072d6072dbe7013e1c42f2ff8`, method,
cut, ordering, seed, bond, cutoff, routing mode, samples, thread request,
memory guard, wall guard, and output directory. The future campaign must first
benchmark one-, two-, and four-NUMA-node execution, distinguishing one large
contraction from independent ensemble jobs. No theoretical scaling assumption
is accepted as evidence.

Promotion gates:

1. reproduce the configuration on the native Apple-Silicon MLX environment;
2. demonstrate later useful-gate progress or stable blind bit information;
3. repeat with an independent seed and preserve the complete telemetry;
4. pass the P9 positive-control gate where the method claims to generalize;
5. only then append executable entries to the manifest.

The current Aer MPS fallback has 1,000 unique samples at bond 64 and threshold
0.01, so it fails gate 2. Native MettleQ MPS runs at the same bond and cutoff
have only 20/36 agreeing modal bits across the initial routing seeds, with mean
absolute marginal difference 0.2375; they also fail gate 2. The later Fiedler
and lookahead probes did not repair this: lookahead-4 failed the P9 control at
both cutoff 0.01 and 0.002. The current MPO baseline timed out at 114/1,413
observed work gates and therefore also fails gate 2.
