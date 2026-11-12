# BarbOS replay results

Cutoff: 2026-09-15T00:00:00-07:00 (Pacific).

Scanned **4,955** .sdfz files. Preserved **1,173** qualifying match entries. Rated **924**; excluded **249** pending review or because the result/layout/data is unsuitable.

Rated results: **428 human wins**, **496 AI wins**. Humans rated: **1,564**.

SMRTBARb +50 is fixed at **mu 21, sigma 1, match rating 20** for each of the eight seats. All rated entities connect to that anchor through the match graph. Human priors are mu 25, sigma 25/3; lobby PvP ratings are preserved as context, not used as BarbOS priors.

## Bonus levels

Every bonus/configuration uses a fixed seed, sigma=1. Non-anchor seeds are provisional training estimates or explicit uncalibrated defaults. Seed sigma is an assigned parameter, not confidence that calibration is accurate.

| Bonus | Match rating (mu-sigma) | mu | sigma | Matches | AI wins |
|---:|---:|---:|---:|---:|---:|
| +30 | 21.09 (fixed) | 22.09 | 1.00 | 9 | 3 |
| +40 | 21.51 (fixed) | 22.51 | 1.00 | 16 | 3 |
| +45 | 21.21 (fixed) | 22.21 | 1.00 | 28 | 13 |
| +48 | 22.70 (fixed) | 23.70 | 1.00 | 1 | 0 |
| +50 | 20.00 (fixed) | 21.00 | 1.00 | 266 | 140 |
| +52 | 21.75 (fixed) | 22.75 | 1.00 | 8 | 4 |
| +55 | 27.16 (fixed) | 28.16 | 1.00 | 193 | 114 |
| +57 | 21.34 (fixed) | 22.34 | 1.00 | 8 | 1 |
| +58 | 27.16 (fixed) | 28.16 | 1.00 | 8 | 6 |
| +60 | 24.69 (fixed) | 25.69 | 1.00 | 196 | 105 |
| +62 | 24.41 (fixed) | 25.41 | 1.00 | 7 | 3 |
| +65 | 27.95 (fixed) | 28.95 | 1.00 | 85 | 52 |
| +69 | 23.47 (fixed) | 24.47 | 1.00 | 4 | 2 |
| +70 | 22.80 (fixed) | 23.80 | 1.00 | 35 | 20 |
| +75 | 22.55 (fixed) | 23.55 | 1.00 | 21 | 10 |
| +80 | 25.90 (fixed) | 26.90 | 1.00 | 11 | 6 |
| +85 | 22.40 (fixed) | 23.40 | 1.00 | 9 | 2 |
| +90 | 24.00 (fixed) | 25.00 | 1.00 | 4 | 2 |
| +100 | 26.93 (fixed) | 27.93 | 1.00 | 15 | 10 |

## Data limits

87 matches have stop/cheat signals. Signals require review and do not establish wrongdoing. Four damaged gzip replays were recovered as partial match entries and excluded. Four in-period zero-byte files have no readable roster or cache and appear only in scan_manifest.json. No actual admin cheating judgments have been entered.

The owner supplied the shared discussion text after the first run. The primary output now implements human-only persistence and frozen versioned opponent seeds. The initial joint-learning run is preserved under data/calibration_baseline. Public ratings and code are published on GitHub; raw replay data remains local.

This is a custom anchored Plackett-Luce run, not BAR's official rating service or an exact reproduction of its server settings. All bot posteriors are discarded. Provisional non-anchor seeds come from a one-pass joint OpenSkill fit to the first 80% of eligible matches; their fitted latent means are retained and seed sigma set to 1. That preliminary fit uses a tied-seat approximation and is not final statistical calibration. Declared AI versions/profiles are keys, but almost all replays omit both. Unknown versions remain explicitly unknown; binary hashes cannot be recovered. Maps are retained for evaluation, not assigned separate human ratings.

## Automatic flags

| Flag | Matches |
|---|---:|
| nondecisive_or_unknown_winner | 161 |
| no_decisive_winner | 158 |
| stop_or_cheat_signal_requires_review | 87 |
| no_startplaying_packet | 58 |
| shared_human_team_requires_model | 10 |
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

Seeds were calibrated on 630 earlier eligible matches; 273 later matches were predicted before their human rating updates.

Mean predicted human win probability: 53.7%; observed human wins: 47.6%. Brier score: 0.296, versus 0.250 for constant 50% predictions (lower is better).

4 heldout matches used at least one uncalibrated default seed. Detailed evaluation by map, configuration, team size and probability bin is in data/prediction_evaluation.json.

**These seeds are provisional and not ready for production rollout.** The forward results do not support treating the predicted win probabilities as calibrated. Full-dataset ratings include in-sample calibration games; only the later evaluation subset is held out from seed fitting.

See README.md for review fields and rerun commands.
