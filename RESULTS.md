# BarbOS replay results

## Primary ratings: all bots learn, +50 fixed (owner 2026-11-12)

The published lists in public/ come from data/varying: every SMRTBARb bonus configuration's mu and sigma vary from match to match; only +50 is fixed at mu 21, sigma 1. Bots start from their seed mean (barbos-fixed-v2) with sigma 25/3. Rated **1,024** matches, **1,730** humans.

Chronological prediction on the last 205 rated matches: Brier 0.237 vs 0.250 for constant 50%; mean predicted human win 48.4%, observed 44.9%.

| Bonus | Match rating (mu-sigma) | mu | sigma | Matches | AI wins |
|---:|---:|---:|---:|---:|---:|
| +10 | 14.50 | 22.79 | 8.29 | 1 | 0 |
| +15 | 18.60 | 26.89 | 8.29 | 1 | 1 |
| +25 | 19.48 | 27.07 | 7.59 | 20 | 12 |
| +30 | 14.47 | 22.47 | 8.00 | 9 | 3 |
| +35 | 21.83 | 28.73 | 6.90 | 52 | 38 |
| +40 | 10.64 | 18.41 | 7.77 | 16 | 3 |
| +45 | 15.45 | 22.74 | 7.29 | 28 | 13 |
| +48 | 14.28 | 22.57 | 8.28 | 1 | 0 |
| +50 | 20.00 (fixed) | 21.00 | 1.00 | 268 | 141 |
| +52 | 15.96 | 23.96 | 8.00 | 8 | 4 |
| +55 | 21.11 | 25.84 | 4.72 | 200 | 120 |
| +57 | 12.97 | 21.06 | 8.09 | 8 | 1 |
| +58 | 19.57 | 27.65 | 8.07 | 8 | 6 |
| +60 | 22.69 | 27.35 | 4.66 | 198 | 107 |
| +62 | 15.82 | 23.85 | 8.03 | 7 | 3 |
| +63 | 12.84 | 20.92 | 8.08 | 9 | 1 |
| +65 | 20.69 | 26.71 | 6.01 | 87 | 52 |
| +68 | 18.01 | 26.25 | 8.24 | 2 | 1 |
| +69 | 16.01 | 24.17 | 8.16 | 4 | 2 |
| +70 | 18.28 | 25.42 | 7.14 | 35 | 20 |
| +75 | 19.18 | 26.67 | 7.49 | 22 | 11 |
| +80 | 17.74 | 25.55 | 7.81 | 12 | 6 |
| +85 | 13.62 | 21.62 | 8.00 | 9 | 2 |
| +90 | 17.61 | 25.77 | 8.16 | 4 | 2 |
| +100 | 19.74 | 27.48 | 7.73 | 15 | 10 |

## Frozen-seed run (previous primary, now public/fixed_seed)


Cutoff: 2026-09-15T00:00:00-07:00 (Pacific).

Scanned **5,155** .sdfz files. Preserved **1,231** qualifying match entries. Rated **1,024**; excluded **207** pending review or because the result/layout/data is unsuitable.

Rated results: **465 human wins**, **559 AI wins**. Humans rated: **1,730**.

SMRTBARb +50 is fixed at **mu 21, sigma 1, match rating 20** for each of the eight seats. All rated entities connect to that anchor through the match graph. Human priors are mu 25, sigma 25/3; lobby PvP ratings are preserved as context, not used as BarbOS priors.

## Bonus levels

Every bonus/configuration uses a fixed seed, sigma=1. Non-anchor seeds are provisional training estimates or explicit uncalibrated defaults. Seed sigma is an assigned parameter, not confidence that calibration is accurate.

| Bonus | Match rating (mu-sigma) | mu | sigma | Matches | AI wins |
|---:|---:|---:|---:|---:|---:|
| +10 | 22.81 (fixed) | 23.81 | 1.00 | 1 | 0 |
| +15 | 24.99 (fixed) | 25.99 | 1.00 | 1 | 1 |
| +25 | 25.86 (fixed) | 26.86 | 1.00 | 20 | 12 |
| +30 | 21.09 (fixed) | 22.09 | 1.00 | 9 | 3 |
| +35 | 27.75 (fixed) | 28.75 | 1.00 | 52 | 38 |
| +40 | 21.51 (fixed) | 22.51 | 1.00 | 16 | 3 |
| +45 | 21.21 (fixed) | 22.21 | 1.00 | 28 | 13 |
| +48 | 22.70 (fixed) | 23.70 | 1.00 | 1 | 0 |
| +50 | 20.00 (fixed) | 21.00 | 1.00 | 268 | 141 |
| +52 | 21.75 (fixed) | 22.75 | 1.00 | 8 | 4 |
| +55 | 27.16 (fixed) | 28.16 | 1.00 | 200 | 120 |
| +57 | 21.34 (fixed) | 22.34 | 1.00 | 8 | 1 |
| +58 | 27.16 (fixed) | 28.16 | 1.00 | 8 | 6 |
| +60 | 24.69 (fixed) | 25.69 | 1.00 | 198 | 107 |
| +62 | 24.41 (fixed) | 25.41 | 1.00 | 7 | 3 |
| +63 | 21.24 (fixed) | 22.24 | 1.00 | 9 | 1 |
| +65 | 27.95 (fixed) | 28.95 | 1.00 | 87 | 52 |
| +68 | 24.74 (fixed) | 25.74 | 1.00 | 2 | 1 |
| +69 | 23.47 (fixed) | 24.47 | 1.00 | 4 | 2 |
| +70 | 22.80 (fixed) | 23.80 | 1.00 | 35 | 20 |
| +75 | 22.55 (fixed) | 23.55 | 1.00 | 22 | 11 |
| +80 | 25.90 (fixed) | 26.90 | 1.00 | 12 | 6 |
| +85 | 22.40 (fixed) | 23.40 | 1.00 | 9 | 2 |
| +90 | 24.00 (fixed) | 25.00 | 1.00 | 4 | 2 |
| +100 | 26.93 (fixed) | 27.93 | 1.00 | 15 | 10 |

## Data limits

91 matches have stop/cheat signals. Signals require review and do not establish wrongdoing. Four damaged gzip replays were recovered as partial match entries and excluded. Four in-period zero-byte files have no readable roster or cache and appear only in scan_manifest.json. No actual admin cheating judgments have been entered.

The owner supplied the shared discussion text after the first run. The primary output now implements human-only persistence and frozen versioned opponent seeds. The initial joint-learning run is preserved under data/calibration_baseline. Public ratings and code are published on GitHub; raw replay data remains local.

This is a custom anchored Plackett-Luce run, not BAR's official rating service or an exact reproduction of its server settings. All bot posteriors are discarded. Provisional non-anchor seeds come from a one-pass joint OpenSkill fit to the first 80% of eligible matches; their fitted latent means are retained and seed sigma set to 1. That preliminary fit uses a tied-seat approximation and is not final statistical calibration. Declared AI versions/profiles are keys, but almost all replays omit both. Unknown versions remain explicitly unknown; binary hashes cannot be recovered. Maps are retained for evaluation, not assigned separate human ratings.

## Automatic flags

| Flag | Matches |
|---|---:|
| nondecisive_or_unknown_winner | 171 |
| no_decisive_winner | 168 |
| stop_or_cheat_signal_requires_review | 91 |
| no_startplaying_packet | 64 |
| shared_human_team_requires_model | 12 |
| human_handicap_requires_model | 8 |
| additional_ai_participants | 7 |
| unsupported_team_layout | 6 |
| compression_integrity_error | 4 |
| truncated_demo_stream | 2 |
| invalid_chunk_length | 1 |
| truncated_chunk_header | 1 |
| duplicate_recording_outcome_disagreement | 1 |

Counts overlap: a match may have several flags.

## Forward evaluation

Seeds were calibrated on 630 earlier eligible matches; 373 later matches were predicted before their human rating updates.

Mean predicted human win probability: 46.3%; observed human wins: 44.8%. Brier score: 0.277, versus 0.250 for constant 50% predictions (lower is better).

4 heldout matches used at least one uncalibrated default seed. Detailed evaluation by map, configuration, team size and probability bin is in data/prediction_evaluation.json.

**These seeds are provisional and not ready for production rollout.** The forward results do not support treating the predicted win probabilities as calibrated. Full-dataset ratings include in-sample calibration games; only the later evaluation subset is held out from seed fitting.

See README.md for review fields and rerun commands.
