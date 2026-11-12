# BarbOS replay dataset and anchored ratings

The working folder is `C:\Users\artib\BAR\BarbOS`. The GitHub repository at https://github.com/Barscrewl/BarbOS was empty when this work began. The code and public ratings are published here. The replay dataset is published without chat as data/matches.json.gz; chat and local calibration artifacts stay local. No game installation was changed.

- [SMRTBARb bonus ratings only](public/barb_bonuses.csv)
- [Match summaries showing each AI team and shared bonus](public/matches.csv)
- [View the ratings list](public/ratings.csv)
- [Ratings with over 15 games (16+), sorted by match rating](public/ratings_over_15_games.csv)
- [All ratings sorted by mu](public/ratings_by_mu.csv)
- [All ratings sorted by leaderboard rating](public/ratings_by_leaderboard_rating.csv)
- [Download ratings CSV](https://raw.githubusercontent.com/Barscrewl/BarbOS/main/public/ratings.csv)
- [Public ratings JSON](public/ratings.json)
- [Results and calibration limitations](RESULTS.md)

These are provisional PvE ratings, not official BAR ratings. Displayed OS is mu minus sigma. Apart from data/matches.json.gz and data/matches_index.csv, the datasets described below are generated locally and are excluded from this repository.

## Published replay dataset

`data/matches.json.gz` is the full qualifying-match dataset (same schema as the local `data/matches.json`) with only the `chat` field removed; `data/matches_index.csv` is its one-row-per-match index. Since 2026-11-12 it combines two machines: VENGEANCE (the owner's PC) and GreenParrots. Each entry's `sources[].machine` says which PC's recording it came from; a game recorded on both PCs is one entry with both sources (match_id is the replay's game ID). To add replays: run `incremental_extract.py <demos folder> <first filename date, e.g. 2026-11-12> <out.json>` on the machine that holds them, then `merge_matches.py <label> <out.json>` on the machine holding `data/`, then `barbos.py rate`, `report.py`, `export_public.py`, `verify_data.py`.

## Files

- `data/matches.json`: one entry per qualifying match, including partial/corrupt matches. Contains starting players and account IDs, all eight AI seats and individual bonuses, spectators, UTC and Pacific timestamps, game/wallclock lengths, map, engine/game version, settings, original lobby cache if available, gameover reports, team/resign/command/disconnect events, chat evidence, source SHA256, review fields and automatic flags.
- `data/matches_index.csv`: compact match index for browsing. Edit reviews in JSON, not this generated CSV.
- `data/bot_seeds.json`: versioned frozen configuration seeds, calibration IDs and provenance.
- `data/prediction_evaluation.json`: chronological heldout prediction evaluation and simple baselines.
- `data/ratings.json` and `data/ratings.csv`: final human and AI-bonus ratings, uncertainty, mu-sigma match rating, mu-3sigma leaderboard rating, win/loss counts, anchor connectivity and run settings.
- `data/rating_history.json`: every rated match, predicted pre-match win probability, before/after mu/sigma, effective admin review and every excluded match/reason.
- `data/admin_reviews.json`: persistent admin corrections keyed by `match_id`. Initially empty: no admin judgments are invented.
- `data/review_queue.json`: excluded match IDs, reasons, and stop evidence.
- `data/scan_manifest.json`: every `.sdfz` examined, including nonqualifying, earlier, and zero-byte recordings. A CRC failure remains recorded even after recovering its partial match entry.
- `data/summary.json`: compact machine-readable run summary.

## Selection and evidence

The cutoff is September 15, 2026 at 00:00 America/Los_Angeles (07:00 UTC). Header timestamps, not filesystem modification times or filenames, decide eligibility. Every `.sdfz` is scanned. A qualifying match has exactly eight AIs whose embedded shortname is SMRTBARb on the same ally team. Extra AIs, no humans, shared human teams and human handicaps are retained and flagged when the current model cannot rate them. Seven-human matches can be rated with their actual seven-versus-eight composition. There is no invented eighth human.

Replay metadata and network packets are read directly without launching BAR or modifying the demos. The cache is supplementary. An absent winner is unknown, not a draw or human resignation. Conflicting winners and malformed or damaged recordings are excluded. Stop requests or votes do not prove a stop was executed or that anyone cheated. All stop/cheat signals are conservatively excluded until reviewed; unrelated stop discussion can be cleared by an admin. Stops without any captured signal may be indistinguishable from other unknown endings. No attempt is made to infer intended winners from score, damage or economy.

Observed results and evidence stay immutable. Admin decisions affect the next full chronological replay of ratings. Starting rosters are used for rating; roster changes and resignation events remain available for review. The engine's header gameTime is the published match duration; packet events additionally carry simulation frames/game seconds and demo time (which includes pregame waiting).

## Admin corrections

Example only (replace the key with a real match ID from `matches_index.csv`):

```json
{
  "MATCH_ID_HERE": {
    "admin_thinks_cheated": true,
    "exclude_from_processing": false,
    "override_termination": "human_resign",
    "reviewed_by": "admin name",
    "reviewed_at": "2026-11-05T12:00:00-08:00",
    "notes": "Reviewed replay: stop was used to avoid a human loss."
  }
}
```

`override_termination: "human_resign"` explicitly records the admin's human-resign label and rates the match as an AI win. `ai_resign` implies a human win. Alternatively set `override_result` to `human_win` or `ai_win`. Conflicting result/termination overrides fail. An override clears outcome/stop ambiguity, but never clears corruption or an unsupported roster. `admin_thinks_cheated: true` alone does not invent a winner. Set `exclude_from_processing: true` to omit any match regardless of its winner. To clear a false-positive stop signal while keeping the observed decisive winner, set `include_despite_automatic_flags: true`; this cannot override corruption, no-start, unknown results, unsupported teams or human handicaps. `override_termination: "stop"` excludes the match.

Reviews in `admin_reviews.json` persist through extraction. The effective review is saved in rating history. Inline `matches.json` review fields are also supported for rating-only runs; extraction rebuilds them and reapplies the persistent review file. Persistent file values take precedence. No admin decision is made automatically.

## Rating policy

**Primary lists since 2026-11-12 (owner's call):** every SMRTBARb bonus configuration learns. Its mu and sigma vary from match to match; only +50 stays fixed at mu 21, sigma 1. `varying_ratings.py` starts each configuration at its seed mean (`barbos-fixed-v2`, sigma 25/3), rates all eight seats with the normal OpenSkill 5.0.1 PlackettLuce update and averages their posteriors once per match. The results are in `data/varying/` and `public/*.csv`. `seeds_v2.py` added seeds for the bonus levels that v1 lacked (+10/+15/+25/+35/+63/+68/+78), using the same anchored joint fit over all eligible matches; the v1 seeds are unchanged and kept in `data/bot_seeds_v1.json`. The frozen-seed, human-only run described below is still produced (`barbos.py rate`) and published in `public/fixed_seed/`.

Rerun order: `barbos.py rate`, `varying_ratings.py`, `report.py`, `export_public.py`, `verify_data.py`.

### Frozen-seed run (previous primary)

The primary run now follows the supplied discussion: separate human PvE ratings, one rating object per actual bot, and **human-only posterior persistence**. It uses `openskill==5.0.1` and `PlackettLuce.rate(teams, ranks=...)` chronologically. The original version was retained because the explicit request linked the 5.0.1 documentation; no silent switch to 6.2.0 was made.

Every bot configuration has a frozen mean and uncertainty in `data/bot_seeds.json`, seed version `barbos-fixed-v1`. Configurations key on shortname, declared AI version, difficulty profile, and bonus. Almost all historical start scripts omit version and profile, so both are explicitly `unknown`; installed modern AI files are not used to invent historical versions. All +50 seeds are enforced at mu=21, sigma=1, displayed rating 20. The other seeds are provisional, not owner-specified strengths.

For every match, recreate each bot from its seed. Run the normal library update, save each human posterior, and discard every bot posterior. No bot mean or sigma changes across matches. The library's default tau applies inside its update, but the seed used for the next match stays unchanged. Human priors are mu=25, sigma=25/3; account IDs keep aliases together. No PvP rating is used as a PvE prior. Display match rating as mu-sigma; mu-3sigma is also supplied separately.

The seed builder uses the first 80% of eligible matches (630 here) for a preliminary joint OpenSkill fit with +50 anchored. Non-anchor seeds retain the fitted **latent mean**, while sigma is set to 1; the calibration fit's mu-sigma ordinal is not copied over as a mean. That fitting step shares AI parameters by averaging per-seat posteriors, so it is an approximation, not maximum-likelihood calibration. Categories absent from training have an explicit default-prior status (mu=25, sigma=1). All seeds then freeze for the entire human-only run. No linear or monotonic bonus-strength curve is assumed.

`data/prediction_evaluation.json` evaluates only the later 158 matches: predict each result before updating that match's humans. It includes Brier score, log loss, reliability bins, and results by map, configuration, and human count, plus constant-50% and training-win-rate baselines. The full dataset ratings include calibration-period matches and are not themselves heldout results. Four heldout matches use an uncalibrated seed; an additional evaluation excludes these. Seed fitting never uses heldout outcomes.

**The provisional seed set is not ready for production.** Heldout Brier score 0.320 is worse than constant-50% predictions at 0.250. Mean predicted human win probability was 50.7%, versus 44.9% observed wins. Use this as a prototype and calibration diagnostic, not evidence that its win probabilities are accurate. Missing historical AI build/profile metadata also limits interpretation.

The original 788-match joint-learning results are preserved in `data/calibration_baseline/`. The training subset, training IDs, fit inputs, fit outputs and calibration source hashes are retained in `data/seed_calibration_v1/` and `bot_seeds.json`. The ratings history records the fixed seed version and each input/posterior. Repeating a run rebuilds human state from scratch rather than double-applying results.

Rerating reuses the existing frozen seed file; it does not silently recalibrate. If admin reviews change after calibration, evaluation records `reviews_changed_since_calibration: true`. A deliberate recalibration must create a new seed version, preserve the previous table, and use earlier calibration data without tuning to the heldout results. An unseen configuration without a seed is excluded rather than automatically changing an existing seed.

## Run again (PowerShell)

```powershell
Set-Location C:\Users\artib\BAR\BarbOS
# Rebuild dataset from all demos, then rate and summarize:
.\.venv\Scripts\python.exe barbos.py all
.\.venv\Scripts\python.exe report.py
# After editing admin_reviews.json, rerate without extracting replays:
.\.venv\Scripts\python.exe barbos.py rate
.\.venv\Scripts\python.exe report.py
# Regression checks:
.\.venv\Scripts\python.exe -m unittest -q test_barbos
```

For a fresh environment, create a venv using Python 3.9+ and install `requirements.txt`. The checked run used Python 3.14.8, OpenSkill 5.0.1 and tzdata 2026.6. Optional `--demos`, `--output`, and `--workers` arguments control source, output and parallel parsing.

Sources: [BAR rating guide](https://www.beyondallreason.info/guide/rating-and-lobby-balance), [OpenSkill installation](https://openskill.me/en/v5.0.1/installation.html), [models API](https://openskill.me/en/v5.0.1/api/openskill/models/index.html), [manual](https://openskill.me/en/v5.0.1/manual.html). Binary parsing follows the locally installed Recoil source definitions under `C:\Users\artib\BAR\bar-RecoilEngine\rts\System\LoadSave\demofile.h` and `rts\Net\Protocol\NetMessageTypes.h` / `BaseNetProtocol.cpp`.

The shared link initially returned only a preview shell. The owner subsequently pasted its discussion, and the primary run was updated to its fixed-seed, human-only persistence policy. No AI/game files were installed or changed.

## Reading SMRTBARb bonuses

Bot instance names such as `SMRTBARbstable(1)` are labels only; they do not identify rated opponents. Rating identity is SMRTBARb plus resource bonus and configuration (with AI version/profile retained when declared). The public CSV now has explicit `entity_type`, `name`, `bonus_percent`, `ai_name`, `ai_version`, and `profile` columns. A bot row reads `AI bonus, SMRTBARb +50, 50, SMRTBARb, unknown, unknown`. Its OS=20 applies to each bot, not to the whole team.

`public/barb_bonuses.csv` contains only the bonus configurations, sorted by bonus. `public/matches.csv` summarizes the AI team: for a uniform team, `8 x SMRTBARb +50` with `shared_bonus_percent=50`; mixed teams show each bonus/count and leave the shared bonus blank. The JSON composition column preserves version/profile for future distinctions without using lobby instance names as identity. Raw data still preserves individual seats and original names for traceability.

Public human rows now also include BAR account IDs, as authorized by the owner. Replay chat remains local. Run `.\.venv\Scripts\python.exe export_public.py` after rerating to refresh all public exports.
