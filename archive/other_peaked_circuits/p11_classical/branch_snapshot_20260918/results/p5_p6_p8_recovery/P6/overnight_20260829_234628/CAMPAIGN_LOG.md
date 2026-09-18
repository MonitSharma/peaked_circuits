# P6 overnight campaign

- 2026-08-29T15:47:56.818097+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T15:52:56.870541+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T15:54:07.895178+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T15:59:07.947463+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T16:04:08.006268+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T16:09:08.056736+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T16:14:08.102874+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T16:19:08.157814+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T16:24:08.208104+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T16:29:08.258694+00:00 Heavy solver active; waiting 300 seconds.

- 2026-08-29T16:34:08.351610+00:00 Idle check 1/2 passed.

- 2026-08-29T16:39:08.426498+00:00 Idle check 2/2 passed.

- 2026-08-29T16:39:08.479398+00:00 Launching stage_a_p6_d512_cut1e3: `/Users/monitsharma/.conda/envs/p9-openblas/bin/python /Users/monitsharma/Code/p12-helios-recovery/scripts/run_p11_mpo.py --solver-root /Users/monitsharma/code_projects/qat/peaked-mpo-solver --qasm /Users/monitsharma/Code/p12-helios-recovery/results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm --outdir /Users/monitsharma/Code/p12-helios-recovery/results/p5_p6_p8_recovery/P6/overnight_20260829_234628/stage_a_p6_d512_cut1e3 --tag stage_a_p6_d512_cut1e3 --threads 3 --rss-soft-gb 20 --rss-limit-gb 24 --wall-limit-s 14400 --samples 1000 --decoder beam --decoder-beam-width 8 --max-bond 512 --cutoff 0.001 --unswap-threshold 500000 --sabre-trials 90 --post-sabre-trials 50 --seed 123 --route-candidates 4 --route-score bond_profile --route-score-lookahead 8 --abort-after-no-progress-unswap-cycles 60 --no-plots`

- 2026-08-29T18:16:58.087586+00:00 Finished stage_a_p6_d512_cut1e3: exit=0, gates=180, complete=False, reason=completed

- 2026-08-29T18:16:58.119972+00:00 Launching stage_b_p6_pair_cut6e4: `/Users/monitsharma/.conda/envs/p9-openblas/bin/python /Users/monitsharma/Code/p12-helios-recovery/scripts/run_p11_mpo.py --solver-root /Users/monitsharma/code_projects/qat/peaked-mpo-solver --qasm /Users/monitsharma/Code/p12-helios-recovery/results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm --outdir /Users/monitsharma/Code/p12-helios-recovery/results/p5_p6_p8_recovery/P6/overnight_20260829_234628/stage_b_p6_pair_cut6e4 --tag stage_b_p6_pair_cut6e4 --threads 3 --rss-soft-gb 20 --rss-limit-gb 24 --wall-limit-s 14400 --samples 1000 --decoder beam --decoder-beam-width 8 --max-bond 512 --cutoff 0.0006 --unswap-threshold 500000 --sabre-trials 90 --post-sabre-trials 50 --seed 123 --route-candidates 4 --route-score bond_profile --route-score-lookahead 8 --abort-after-no-progress-unswap-cycles 60 --no-plots --unswap-select-mode pair_lookahead --unswap-pair-lookahead-limit 8`

- 2026-08-29T22:17:07.693431+00:00 Finished stage_b_p6_pair_cut6e4: exit=1, gates=24, complete=False, reason=wall_limit

- 2026-08-29T22:17:07.737027+00:00 Launching stage_c_p6_pair_cut1e3: `/Users/monitsharma/.conda/envs/p9-openblas/bin/python /Users/monitsharma/Code/p12-helios-recovery/scripts/run_p11_mpo.py --solver-root /Users/monitsharma/code_projects/qat/peaked-mpo-solver --qasm /Users/monitsharma/Code/p12-helios-recovery/results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm --outdir /Users/monitsharma/Code/p12-helios-recovery/results/p5_p6_p8_recovery/P6/overnight_20260829_234628/stage_c_p6_pair_cut1e3 --tag stage_c_p6_pair_cut1e3 --threads 3 --rss-soft-gb 20 --rss-limit-gb 24 --wall-limit-s 10800 --samples 1000 --decoder beam --decoder-beam-width 8 --max-bond 512 --cutoff 0.001 --unswap-threshold 500000 --sabre-trials 90 --post-sabre-trials 50 --seed 123 --route-candidates 4 --route-score bond_profile --route-score-lookahead 8 --abort-after-no-progress-unswap-cycles 60 --no-plots --unswap-select-mode pair_lookahead --unswap-pair-lookahead-limit 8`

- 2026-08-30T00:05:00+00:00 User requested campaign stop. Terminated the active Stage C solver and controller; preserved all artifacts. No portal submission made.
