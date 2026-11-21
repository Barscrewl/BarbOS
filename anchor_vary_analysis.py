"""Analysis (owner 2026-11-20): does letting SMRTBARb +50 vary after a 21/1 seed predict better?

Replays every eligible match chronologically (same rules and model as varying_ratings.py) under:
  A  current  : +50 fixed at mu 21, sigma 1 (published method)
  B  seed-vary: +50 starts at mu 21, sigma 1, then mu AND sigma update like every other barb
  C  wide-vary: +50 starts at mu 21, sigma 25/3, then varies (sensitivity: what if the seed is not tight)
Every prediction is made before that match updates anyone (no look-ahead).
Scored on all matches, and per player-game for humans with more than 15 games (owner's filter).
Writes data/analysis_anchor_vary/{summary.json,REPORT.md}."""
import collections, json, math
from openskill.models import PlackettLuce
import barbos, fixed_ratings as fr

ROOT = barbos.ROOT / 'data'
WIDE = 25 / 3


def replay(variant, dataset, reviews, seeds):
    model = PlackettLuce(); state = {}; rows = []
    def start(key):
        if key == fr.ANCHOR: return (21.0, WIDE if variant == 'C' else 1.0)
        if key.startswith('ai:'):
            s = seeds['seeds'].get(key); return (s['mu'] if s else 25.0, WIDE)
        return (25.0, WIDE)
    for m in sorted(dataset['matches'], key=lambda m: (m['started_at_utc'], m['match_id'])):
        result, reasons, _ = barbos.effective(m, reviews)
        if reasons: continue
        hkeys = [p['rating_key'] for p in m['players']]
        akeys = [fr.config_key(fr.configuration(a)) for a in m['ais']]
        for k in hkeys + akeys: state.setdefault(k, start(k))
        hp = [model.rating(mu=state[k][0], sigma=state[k][1]) for k in hkeys]
        bots = [model.rating(mu=state[k][0], sigma=state[k][1]) for k in akeys]
        p = model.predict_win([hp, bots])[0]
        y = int(result == 'human_win')
        anchor_before = state.get(fr.ANCHOR)
        rows.append(dict(match_id=m['match_id'], t=m['started_at_utc'], p=p, y=y, humans=hkeys,
                         pure50=set(akeys) == {fr.ANCHOR},
                         human_os={k: state[k][0] - state[k][1] for k in hkeys},
                         barb_os=sum(state[k][0] - state[k][1] for k in akeys) / len(akeys)))
        new_h, new_b = model.rate([hp, bots], ranks=[1, 2] if y else [2, 1])
        grouped = collections.defaultdict(list)
        for k, r in zip(hkeys + akeys, list(new_h) + list(new_b)): grouped[k].append(r)
        for k, rs in grouped.items():
            if k == fr.ANCHOR and variant == 'A': state[k] = (21.0, 1.0)
            else: state[k] = (sum(r.mu for r in rs) / len(rs), sum(r.sigma for r in rs) / len(rs))
    return rows, state


def metrics(ps, ys):
    n = len(ps)
    if not n: return dict(n=0)
    brier = sum((p - y) ** 2 for p, y in zip(ps, ys)) / n
    ll = -sum(y * math.log(max(p, 1e-12)) + (1 - y) * math.log(max(1 - p, 1e-12)) for p, y in zip(ps, ys)) / n
    acc = sum((p >= 0.5) == bool(y) for p, y in zip(ps, ys)) / n
    pos = [p for p, y in zip(ps, ys) if y]; neg = [p for p, y in zip(ps, ys) if not y]
    auc = (sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))) if pos and neg else None
    base = sum(ys) / n
    return dict(n=n, observed=base, mean_pred=sum(ps) / n, brier=brier, log_loss=ll, accuracy=acc, auc=auc,
                brier_skill_vs_base_rate=1 - brier / (base * (1 - base)) if 0 < base < 1 else None)


def bins(ps, ys, edges=(0, .2, .4, .6, .8, .9, 1.0001)):
    out = []
    for lo, hi in zip(edges, edges[1:]):
        sel = [(p, y) for p, y in zip(ps, ys) if lo <= p < hi]
        if sel: out.append(dict(range=f'{lo:.0%}-{min(hi,1):.0%}', n=len(sel), predicted=sum(p for p, _ in sel) / len(sel), actual=sum(y for _, y in sel) / len(sel)))
    return out


def main():
    dataset = json.loads((ROOT / 'matches.json').read_text(encoding='utf8'))
    reviews = json.loads((ROOT / 'admin_reviews.json').read_text(encoding='utf8'))
    seeds = json.loads((ROOT / 'bot_seeds.json').read_text(encoding='utf8'))
    runs = {v: replay(v, dataset, reviews, seeds) for v in 'ABC'}
    rowsA = runs['A'][0]
    games = collections.Counter(k for r in rowsA for k in set(r['humans']))
    vets = {k for k, n in games.items() if n > 15}
    split = int(len(rowsA) * 0.8)
    summary = dict(rated_matches=len(rowsA), veteran_players=len(vets), holdout_from=rowsA[split]['t'], variants={})
    for v, (rows, state) in runs.items():
        sets = {
            'all_matches': rows,
            'pure_plus50_matches': [r for r in rows if r['pure50']],
            'holdout_last_20pct': rows[split:],
        }
        res = {name: metrics([r['p'] for r in rs], [r['y'] for r in rs]) for name, rs in sets.items()}
        # player-games of humans with > 15 games: one row per (match, veteran) using that match's prediction
        pg = [(r['p'], r['y'], r) for r in rows for k in r['humans'] if k in vets]
        res['veteran_player_games'] = metrics([p for p, _, _ in pg], [y for _, y, _ in pg])
        pgh = [(r['p'], r['y']) for r in rows[split:] for k in r['humans'] if k in vets]
        res['veteran_player_games_holdout'] = metrics([p for p, _ in pgh], [y for _, y in pgh])
        # matches where at least half the humans are veterans
        mv = [r for r in rows if sum(k in vets for k in r['humans']) * 2 >= len(r['humans'])]
        res['matches_majority_veterans'] = metrics([r['p'] for r in mv], [r['y'] for r in mv])
        res['calibration_veteran_player_games'] = bins([p for p, _, _ in pg], [y for _, y, _ in pg])
        res['calibration_pure_plus50'] = bins([r['p'] for r in sets['pure_plus50_matches']], [r['y'] for r in sets['pure_plus50_matches']])
        # does the veteran's own pre-match OS (vs barb OS) rank wins? per player-game AUC
        osd = [(r['human_os'][k] - r['barb_os'], r['y']) for r in rows for k in r['humans'] if k in vets]
        res['veteran_os_minus_barb_os_auc'] = metrics([1 / (1 + math.exp(-d / 4)) for d, _ in osd], [y for _, y in osd])['auc']
        a = state[fr.ANCHOR]
        res['final_plus50'] = dict(mu=a[0], sigma=a[1], os=a[0] - a[1])
        vet_os = sorted(state[k][0] - state[k][1] for k in vets)
        res['veteran_final_os_median'] = vet_os[len(vet_os) // 2]
        res['veteran_final_mu_median'] = sorted(state[k][0] for k in vets)[len(vets) // 2]
        summary['variants'][v] = res
    out = ROOT / 'analysis_anchor_vary'; out.mkdir(exist_ok=True)
    barbos.dump(out / 'summary.json', summary)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__': main()
