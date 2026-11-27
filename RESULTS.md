# BarbOS replay results

## Primary ratings: all bots learn, +50 seeded 21 then varies (owner 2026-11-24)

The published lists in public/ come from data/varying: every SMRTBARb bonus configuration's mu and sigma vary from match to match; +50 starts at mu 21, sigma 25/3 and varies too (fixed at 21/1 until 2026-11-24). Bots start from their seed mean (barbos-fixed-v2) with sigma 25/3. Rated **1,347** matches, **2,091** humans.

Chronological prediction on the last 270 rated matches: Brier 0.191 vs 0.250 for constant 50%; mean predicted human win 39.9%, observed 42.6%.

| Bonus | Match rating (mu-sigma) | mu | sigma | Matches | AI wins |
|---:|---:|---:|---:|---:|---:|
| +10 | 14.58 | 22.87 | 8.29 | 1 | 0 |
| +15 | 18.68 | 26.97 | 8.29 | 1 | 1 |
| +20 | 15.46 | 23.75 | 8.29 | 1 | 0 |
| +25 | 20.62 | 27.75 | 7.12 | 37 | 24 |
| +30 | 17.90 | 25.15 | 7.25 | 32 | 18 |
| +35 | 22.98 | 29.19 | 6.20 | 92 | 68 |
| +39 | 16.79 | 24.91 | 8.12 | 5 | 3 |
| +40 | 12.15 | 19.84 | 7.69 | 20 | 4 |
| +45 | 16.61 | 23.89 | 7.29 | 28 | 13 |
| +48 | 14.45 | 22.73 | 8.28 | 1 | 0 |
| +50 | 23.37 | 27.04 | 3.67 | 428 | 232 |
| +51 | 16.20 | 24.50 | 8.30 | 1 | 0 |
| +52 | 15.93 | 23.91 | 7.98 | 9 | 4 |
| +53 | 16.78 | 24.94 | 8.16 | 6 | 1 |
| +55 | 23.10 | 27.53 | 4.43 | 246 | 151 |
| +57 | 17.59 | 25.36 | 7.77 | 20 | 6 |
| +58 | 20.41 | 28.45 | 8.05 | 8 | 6 |
| +59 | 17.57 | 25.86 | 8.29 | 1 | 1 |
| +60 | 23.22 | 27.83 | 4.61 | 207 | 111 |
| +62 | 16.37 | 24.41 | 8.03 | 7 | 3 |
| +63 | 13.47 | 21.59 | 8.12 | 9 | 1 |
| +65 | 21.59 | 27.56 | 5.97 | 88 | 52 |
| +68 | 18.25 | 26.50 | 8.25 | 2 | 1 |
| +69 | 16.10 | 24.26 | 8.16 | 4 | 2 |
| +70 | 21.52 | 28.59 | 7.07 | 37 | 22 |
| +75 | 20.40 | 27.91 | 7.52 | 22 | 11 |
| +80 | 18.86 | 26.67 | 7.81 | 12 | 6 |
| +85 | 14.21 | 22.22 | 8.02 | 9 | 2 |
| +90 | 18.09 | 26.26 | 8.17 | 4 | 2 |
| +100 | 20.61 | 28.33 | 7.72 | 15 | 10 |

## Frozen-seed run (previous primary, now public/fixed_seed)


Cutoff: 2026-09-15T00:00:00-07:00 (Pacific).

Scanned **5,578** .sdfz files. Preserved **1,646** qualifying match entries. Rated **1,333**; excluded **313** pending review or because the result/layout/data is unsuitable.

Rated results: **587 human wins**, **746 AI wins**. Humans rated: **2,079**.

SMRTBARb +50 is fixed at **mu 21, sigma 1, match rating 20** for each of the eight seats. All rated entities connect to that anchor through the match graph. Human priors are mu 25, sigma 25/3; lobby PvP ratings are preserved as context, not used as BarbOS priors.

## Bonus levels

Every bonus/configuration uses a fixed seed, sigma=1. Non-anchor seeds are provisional training estimates or explicit uncalibrated defaults. Seed sigma is an assigned parameter, not confidence that calibration is accurate.

| Bonus | Match rating (mu-sigma) | mu | sigma | Matches | AI wins |
|---:|---:|---:|---:|---:|---:|
| +10 | 22.81 (fixed) | 23.81 | 1.00 | 1 | 0 |
| +15 | 24.99 (fixed) | 25.99 | 1.00 | 1 | 1 |
| +25 | 25.86 (fixed) | 26.86 | 1.00 | 37 | 24 |
| +30 | 21.09 (fixed) | 22.09 | 1.00 | 27 | 15 |
| +35 | 27.75 (fixed) | 28.75 | 1.00 | 92 | 68 |
| +40 | 21.51 (fixed) | 22.51 | 1.00 | 20 | 4 |
| +45 | 21.21 (fixed) | 22.21 | 1.00 | 28 | 13 |
| +48 | 22.70 (fixed) | 23.70 | 1.00 | 1 | 0 |
| +50 | 20.00 (fixed) | 21.00 | 1.00 | 428 | 232 |
| +52 | 21.75 (fixed) | 22.75 | 1.00 | 9 | 4 |
| +55 | 27.16 (fixed) | 28.16 | 1.00 | 246 | 151 |
| +57 | 21.34 (fixed) | 22.34 | 1.00 | 20 | 6 |
| +58 | 27.16 (fixed) | 28.16 | 1.00 | 8 | 6 |
| +60 | 24.69 (fixed) | 25.69 | 1.00 | 207 | 111 |
| +62 | 24.41 (fixed) | 25.41 | 1.00 | 7 | 3 |
| +63 | 21.24 (fixed) | 22.24 | 1.00 | 9 | 1 |
| +65 | 27.95 (fixed) | 28.95 | 1.00 | 88 | 52 |
| +68 | 24.74 (fixed) | 25.74 | 1.00 | 2 | 1 |
| +69 | 23.47 (fixed) | 24.47 | 1.00 | 4 | 2 |
| +70 | 22.80 (fixed) | 23.80 | 1.00 | 37 | 22 |
| +75 | 22.55 (fixed) | 23.55 | 1.00 | 22 | 11 |
| +80 | 25.90 (fixed) | 26.90 | 1.00 | 12 | 6 |
| +85 | 22.40 (fixed) | 23.40 | 1.00 | 9 | 2 |
| +90 | 24.00 (fixed) | 25.00 | 1.00 | 4 | 2 |
| +100 | 26.93 (fixed) | 27.93 | 1.00 | 15 | 10 |

## Data limits

123 matches have stop/cheat signals. Signals require review and do not establish wrongdoing. Four damaged gzip replays were recovered as partial match entries and excluded. Four in-period zero-byte files have no readable roster or cache and appear only in scan_manifest.json. No actual admin cheating judgments have been entered.

The owner supplied the shared discussion text after the first run. The primary output now implements human-only persistence and frozen versioned opponent seeds. The initial joint-learning run is preserved under data/calibration_baseline. Public ratings and code are published on GitHub; raw replay data remains local.

This is a custom anchored Plackett-Luce run, not BAR's official rating service or an exact reproduction of its server settings. All bot posteriors are discarded. Provisional non-anchor seeds come from a one-pass joint OpenSkill fit to the first 80% of eligible matches; their fitted latent means are retained and seed sigma set to 1. That preliminary fit uses a tied-seat approximation and is not final statistical calibration. Declared AI versions/profiles are keys, but almost all replays omit both. Unknown versions remain explicitly unknown; binary hashes cannot be recovered. Maps are retained for evaluation, not assigned separate human ratings.

## Automatic flags

| Flag | Matches |
|---|---:|
| nondecisive_or_unknown_winner | 254 |
| no_decisive_winner | 251 |
| stop_or_cheat_signal_requires_review | 123 |
| no_startplaying_packet | 108 |
| shared_human_team_requires_model | 33 |
| additional_ai_participants | 8 |
| human_handicap_requires_model | 8 |
| unsupported_team_layout | 7 |
| compression_integrity_error | 4 |
| truncated_demo_stream | 2 |
| duplicate_recording_outcome_disagreement | 2 |
| invalid_chunk_length | 1 |
| truncated_chunk_header | 1 |

Counts overlap: a match may have several flags.

## Forward evaluation

Seeds were calibrated on 630 earlier eligible matches; 682 later matches were predicted before their human rating updates.

Mean predicted human win probability: 50.9%; observed human wins: 42.4%. Brier score: 0.280, versus 0.250 for constant 50% predictions (lower is better).

4 heldout matches used at least one uncalibrated default seed. Detailed evaluation by map, configuration, team size and probability bin is in data/prediction_evaluation.json.

**These seeds are provisional and not ready for production rollout.** The forward results do not support treating the predicted win probabilities as calibrated. Full-dataset ratings include in-sample calibration games; only the later evaluation subset is held out from seed fitting.

See README.md for review fields and rerun commands.
