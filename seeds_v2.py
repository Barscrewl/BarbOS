"""Add seeds for bot configurations that barbos-fixed-v1 lacks, with the same algorithm
(anchored joint OpenSkill fit, +50 = mu 21 sigma 1, fitted latent mu kept, seed sigma 1).
v1 only fitted on the first 80% of the Nov 5 data, so configurations first seen later get
their fit from all eligible matches. Existing v1 seeds are kept unchanged.
Writes data/bot_seeds.json as barbos-fixed-v2; v1 is preserved as data/bot_seeds_v1.json."""
import contextlib, datetime as dt, hashlib, io, json, pathlib, shutil
import barbos, fixed_ratings as fr

def main():
    folder = barbos.ROOT / 'data'
    v1_path = folder / 'bot_seeds_v1.json'
    if not v1_path.exists(): shutil.copy2(folder / 'bot_seeds.json', v1_path)
    v1 = json.loads(v1_path.read_text(encoding='utf8'))
    dataset = json.loads((folder / 'matches.json').read_text(encoding='utf8'))
    reviews = json.loads((folder / 'admin_reviews.json').read_text(encoding='utf8'))
    configs = {fr.config_key(fr.configuration(a)): fr.configuration(a) for m in dataset['matches'] for a in m['ais']
               if a.get('short_name', 'SMRTBARb').casefold() == 'smrtbarb'}
    missing = {k: c for k, c in configs.items() if k not in v1['seeds']}
    eligible = [m for m in sorted(dataset['matches'], key=lambda m: (m['started_at_utc'], m['match_id']))
                if not barbos.effective(m, reviews)[1]]
    fit = folder / 'seed_calibration_v2'; fit.mkdir(exist_ok=True)
    lite = []
    for m in eligible:
        row = {k: m[k] for k in ('match_id', 'started_at_utc', 'started_at_local', 'map', 'players', 'ais', 'review', 'automatic_flags', 'observed_outcome', 'review_signals')}
        row['ais'] = [a | {'rating_key': fr.config_key(fr.configuration(a))} for a in m['ais']]
        for a in row['ais']:
            if fr.configuration(a)['bonus_percent'] == 50: a['rating_key'] = 'ai:SMRTBARb:bonus:50'
        lite.append(row)
    barbos.dump(fit / 'matches.json', dict(matches=lite)); barbos.dump(fit / 'admin_reviews.json', {})
    with contextlib.redirect_stdout(io.StringIO()): barbos.rate_calibration(type('Args', (), {'output': fit})())
    by_key = {r['key']: r for r in json.loads((fit / 'ratings.json').read_text(encoding='utf8'))['ratings']}
    seeds = dict(v1['seeds'])
    for key, config in missing.items():
        r = by_key.get(key)
        seeds[key] = dict(configuration=config, mu=r['mu'] if r else 25.0, sigma=1.0, match_rating=(r['mu'] if r else 25.0) - 1,
                          seed_status='provisional_full_data_estimate' if r else 'uncalibrated_default_prior',
                          calibration_games=r['games'] if r else 0, added_in='barbos-fixed-v2')
    doc = dict(v1, seed_version='barbos-fixed-v2', created_at=dt.datetime.now(barbos.TZ).isoformat(), seeds=seeds,
               v2_note='v1 seeds unchanged. Configurations first seen after the v1 calibration were fitted with the same anchored joint fit over all eligible matches (in-sample).',
               v2_calibration_dataset_sha256=hashlib.sha256((fit / 'matches.json').read_bytes()).hexdigest(),
               v2_added=sorted(missing))
    barbos.dump(folder / 'bot_seeds.json', doc)
    for k in sorted(missing): print(k, round(seeds[k]['mu'], 3), seeds[k]['seed_status'], seeds[k]['calibration_games'])

if __name__ == '__main__': main()
