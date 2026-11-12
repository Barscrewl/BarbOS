"""Primary BarbOS run (owner 2026-11-12): every bot configuration's mu AND sigma vary
across matches; only SMRTBARb +50 stays fixed at mu 21, sigma 1.

Same OpenSkill 5.0.1 PlackettLuce, chronological, starting rosters, same exclusions.
Each bot configuration starts from its seed mean in data/bot_seeds.json with the default
prior uncertainty sigma 25/3, so it can move. Its eight seats are rated as eight
players; their posteriors are averaged once per match into the configuration's state
(the same tied-seat update as the original joint run). Humans: mu 25, sigma 25/3.
Writes data/varying/{ratings.json,rating_history.json,prediction_evaluation.json,ratings.csv}."""
import collections, csv, datetime as dt, hashlib, json, math
import openskill
from openskill.models import PlackettLuce
import barbos, fixed_ratings as fr

BOT_START_SIGMA = 25 / 3

def run(folder=barbos.ROOT / 'data'):
    if openskill.__version__ != '5.0.1': raise ValueError('Requires openskill==5.0.1')
    out = folder / 'varying'; out.mkdir(exist_ok=True)
    source = folder / 'matches.json'; dataset = json.loads(source.read_text(encoding='utf8'))
    reviews = json.loads((folder / 'admin_reviews.json').read_text(encoding='utf8'))
    seed_path = folder / 'bot_seeds.json'; seeds = json.loads(seed_path.read_text(encoding='utf8'))
    model = PlackettLuce(); state = {}; records = {}; history = []; excluded = []; graph = collections.defaultdict(set)
    anchor = fr.ANCHOR

    def start(key):
        if key == anchor: return (21.0, 1.0)
        if key.startswith('ai:'):
            seed = seeds['seeds'].get(key)
            return (seed['mu'] if seed else 25.0, BOT_START_SIGMA)
        return (25.0, 25 / 3)

    def get(key, name):
        if key not in state:
            state[key] = start(key)
            records[key] = dict(key=key, names=[], games=0, wins=0, losses=0, seat_appearances=0, first_match=None, last_match=None,
                                fixed=key == anchor, start_mu=state[key][0], start_sigma=state[key][1],
                                seed_status=seeds['seeds'].get(key, {}).get('seed_status') if key.startswith('ai:') else None,
                                seed_version=seeds['seed_version'] if key.startswith('ai:') else None)
        if name not in records[key]['names']: records[key]['names'].append(name)
        mu, sigma = state[key]
        return model.rating(mu=mu, sigma=sigma, name=key)

    for m in sorted(dataset['matches'], key=lambda m: (m['started_at_utc'], m['match_id'])):
        result, reasons, review = barbos.effective(m, reviews)
        if reasons:
            excluded.append(dict(match_id=m['match_id'], started_at_local=m['started_at_local'], map=m['map'], observed_result=m['observed_outcome']['result'], reasons=reasons, review_signals=m['review_signals'], review=review))
            continue
        hkeys = [p['rating_key'] for p in m['players']]
        akeys = [fr.config_key(fr.configuration(a)) for a in m['ais']]
        hp = [get(k, p['name']) for k, p in zip(hkeys, m['players'])]
        bots = [get(k, (seeds['seeds'].get(k) or {}).get('configuration', {}).get('short_name', 'SMRTBARb') + f" +{fr.configuration(a)['bonus_percent']:g}") for k, a in zip(akeys, m['ais'])]
        before = {r.name: (r.mu, r.sigma) for r in hp + bots}
        keys = list(before)
        for k in keys: graph[keys[0]].add(k); graph[k].add(keys[0])
        predicted = model.predict_win([hp, bots])[0]
        ranks = [1, 2] if result == 'human_win' else [2, 1]
        new_h, new_b = model.rate([hp, bots], ranks=ranks)
        grouped = collections.defaultdict(list)
        for k, r in zip(hkeys + akeys, list(new_h) + list(new_b)): grouped[k].append(r)
        counts = collections.Counter(hkeys + akeys); deltas = []
        for key, rs in grouped.items():
            if key == anchor: state[key] = (21.0, 1.0)
            else: state[key] = (sum(r.mu for r in rs) / len(rs), sum(r.sigma for r in rs) / len(rs))
            rec = records[key]; rec['games'] += 1; rec['seat_appearances'] += counts[key]
            win = (not key.startswith('ai:')) == (result == 'human_win')
            rec['wins'] += int(win); rec['losses'] += int(not win)
            rec['first_match'] = rec['first_match'] or m['started_at_utc']; rec['last_match'] = m['started_at_utc']
            deltas.append(dict(key=key, before_mu=before[key][0], before_sigma=before[key][1], after_mu=state[key][0], after_sigma=state[key][1], mu_delta=state[key][0] - before[key][0], seat_count=counts[key], fixed=key == anchor))
        assert state.get(anchor, (21.0, 1.0)) == (21.0, 1.0)
        history.append(dict(match_id=m['match_id'], started_at_utc=m['started_at_utc'], map=m['map'], human_count=len(hp), ai_count=len(bots), ai_keys=sorted(set(akeys)), result=result, ranks=ranks, predicted_human_win_probability=predicted, ratings=deltas, review=review))

    get(anchor, 'SMRTBARb +50')
    anchored = set(); pending = [anchor]
    while pending:
        key = pending.pop()
        if key in anchored: continue
        anchored.add(key); pending.extend(graph[key] - anchored)
    ratings = []
    for key, rec in records.items():
        mu, sigma = state[key]
        ratings.append(rec | dict(mu=mu, sigma=sigma, match_rating=mu - sigma, leaderboard_rating=mu - 3 * sigma, connected_to_anchor=key in anchored))
    ratings.sort(key=lambda r: r['match_rating'], reverse=True)
    metadata = dict(generated_at=dt.datetime.now(barbos.TZ).isoformat(), openskill_version=openskill.__version__, model='PlackettLuce',
                    policy='All bot configurations learn (mu and sigma vary); only SMRTBARb +50 fixed at mu 21, sigma 1. Human posteriors persist.',
                    parameters=dict(mu=25, sigma=25 / 3, beta=25 / 6, tau=25 / 300, kappa=0.0001),
                    anchor=dict(key=anchor, mu=21, sigma=1, match_rating=20, per_ai_seat=True),
                    human_initial_prior=dict(mu=25, sigma=25 / 3),
                    bot_initial_prior=dict(mu='seed mean from bot_seeds.json (25 if none)', sigma=BOT_START_SIGMA),
                    shared_ai_parameter_update='Average posterior mu and sigma across the seats of each configuration, once per match (tied-seat approximation).',
                    seed_version=seeds['seed_version'], seed_file_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),
                    rating_scale=dict(match='mu - sigma', leaderboard='mu - 3*sigma'),
                    matches_rated=len(history), matches_excluded=len(excluded),
                    entities_disconnected_from_anchor=sum(not r['connected_to_anchor'] for r in ratings),
                    human_count=sum(not r['key'].startswith('ai:') for r in ratings),
                    dataset_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    reviews_sha256=hashlib.sha256((folder / 'admin_reviews.json').read_bytes()).hexdigest())
    barbos.dump(out / 'ratings.json', dict(metadata=metadata, ratings=ratings))
    barbos.dump(out / 'rating_history.json', dict(metadata=metadata, matches=history, excluded=excluded))
    with (out / 'ratings.csv').open('w', encoding='utf-8-sig', newline='') as f:
        fields = ['key', 'names', 'mu', 'sigma', 'match_rating', 'leaderboard_rating', 'games', 'wins', 'losses', 'seat_appearances', 'fixed', 'start_mu', 'start_sigma', 'seed_status', 'seed_version']
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader()
        for r in ratings: w.writerow(r | {'names': ' | '.join(r['names'])})
    split = int(len(history) * 0.8); holdout = history[split:]
    evaluation = dict(note='Chronological: each prediction is made before that match updates anyone. "holdout" = last 20% of rated matches.',
                      all_matches=fr.score(history), training_matches=split, holdout=fr.score(holdout),
                      constant_50_percent_baseline=fr.score([m | {'predicted_human_win_probability': 0.5} for m in holdout]),
                      uncalibrated_holdout_matches=0)
    barbos.dump(out / 'prediction_evaluation.json', evaluation)
    print(json.dumps(dict(rated=len(history), excluded=len(excluded), humans=metadata['human_count'], holdout=evaluation['holdout'], all=evaluation['all_matches']), indent=1))
    for r in sorted((r for r in ratings if r['key'].startswith('ai:')), key=lambda r: float(r['key'].rsplit(':', 1)[1])):
        print(f"{r['key'].rsplit(':',1)[1]:>4} mu {r['mu']:6.2f} sigma {r['sigma']:5.2f} OS {r['match_rating']:6.2f} games {r['games']:4d} (start {r['start_mu']:.2f})")

if __name__ == '__main__': run()
