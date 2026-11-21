"""Win chance for a roster: humans (looked up in BarbOS) versus barbs (SMRTBARb at a bonus).

Uses the same model and call as the sync's varying run (varying_ratings.py): OpenSkill 5.0.1
PlackettLuce, model.predict_win([humans, barbs]), with every barb seat as its own player at that
bonus's current mu/sigma. Ratings come from data/varying/ratings.json (rewritten by every sync).
Unknown humans get the new-player prior (mu 25, sigma 25/3), the same start a first game gets.
A bonus never rated yet starts from its seed mean in data/bot_seeds.json with sigma 25/3.

  python predict_win.py --humans "Sinbearer,quejour,CH13F" --barbs 55           (8 barbs at +55)
  python predict_win.py --humans a,b --barbs 2x55,1x60     (or 55,55,60)        --json for machine output
"""
import argparse, json, re, sys
from pathlib import Path
import openskill
from openskill.models import PlackettLuce

ROOT = Path(__file__).resolve().parent
NEW_MU, NEW_SIGMA = 25.0, 25 / 3
ANCHOR_BONUS = 50


def norm(n): return n.strip().lower()
def untag(n): return re.sub(r'^\[[^\]]*\]', '', norm(n))


REPO = 'Barscrewl/BarbOS'
CACHE = ROOT.parent / 'BarbOS-sync' / 'github_ratings.json'


def fetch_github():
    """Latest public/ratings.json from GitHub main, read at the newest commit sha (no raw CDN lag)."""
    import urllib.request
    def get(url):
        req = urllib.request.Request(url, headers={'User-Agent': 'barbos-predict'})
        with urllib.request.urlopen(req, timeout=15) as r: return r.read()
    try: sha = json.loads(get(f'https://api.github.com/repos/{REPO}/commits/main'))['sha']
    except Exception: sha = 'main'
    data = json.loads(get(f'https://raw.githubusercontent.com/{REPO}/{sha}/public/ratings.json'))
    return data, sha


def load(folder, source):
    seeds = json.loads((folder / 'bot_seeds.json').read_text(encoding='utf8'))['seeds']
    humans, bots = {}, {}
    def add_human(r, names):
        for n in names:
            k = norm(n)
            if k not in humans or r['games'] > humans[k]['games']: humans[k] = r | {'names': names}
    if source == 'local':
        ratings = json.loads((folder / 'varying' / 'ratings.json').read_text(encoding='utf8'))
        for r in ratings['ratings']:
            if r['key'].startswith('ai:'):
                m = re.search(r':bonus:([\d.]+)$', r['key'])
                if m and ':SMRTBARb:' in r['key']: bots[float(m.group(1))] = r
            else: add_human(r, r['names'])
        m = ratings['metadata']
        return f"local data/varying ({m.get('generated_at','?')[:16]}, {m.get('matches_rated')} games rated)", humans, bots, seeds
    try:
        data, sha = fetch_github(); CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(dict(sha=sha, data=data)), encoding='utf8'); where = f'GitHub {REPO}@{sha[:7]}'
    except Exception as e:
        if not CACHE.exists(): raise SystemExit(f'GitHub fetch failed ({e}) and no cache; use --source local')
        c = json.loads(CACHE.read_text(encoding='utf8')); data, sha = c['data'], c['sha']
        where = f'cached GitHub {REPO}@{sha[:7]} (fetch failed: {e})'
    for r in data['ratings']:
        if r['entity_type'] == 'human': add_human(r, [n.strip() for n in str(r['names']).split('|') if n.strip()] or [r['name']])
        elif r.get('ai_name') == 'SMRTBARb' and r.get('bonus_percent') is not None: bots[float(r['bonus_percent'])] = r
    return where, humans, bots, seeds


def find_human(name, humans):
    r = humans.get(norm(name))
    if r: return r
    hits = {id(v): v for k, v in humans.items() if untag(k) == untag(name)}
    return next(iter(hits.values())) if len(hits) == 1 else None


def parse_barbs(spec, count):
    out = []
    for part in [p for p in re.split(r'[,\s]+', spec.strip()) if p]:
        m = re.fullmatch(r'(?:(\d+)[x*])?\+?([\d.]+)', part, re.I)
        if not m: raise SystemExit(f'bad barb spec: {part!r} (use 55, 8x55 or 2x55,1x60)')
        out += [float(m.group(2))] * int(m.group(1) or 1)
    if len(out) == 1 and count: out *= count
    return out


def bot_rating(bonus, bots, seeds):
    if bonus == ANCHOR_BONUS: return 21.0, 1.0, 'fixed anchor'
    r = bots.get(bonus)
    if r: return r['mu'], r['sigma'], f"{r['games']} games"
    seed = next((s for k, s in seeds.items() if k.endswith(f':bonus:{bonus:g}')), None)
    return (seed['mu'] if seed else 25.0), NEW_SIGMA, 'never rated (seed start)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--humans', required=True, help='comma-separated player names')
    ap.add_argument('--barbs', required=True, help='bonus: 55 | 8x55 | 2x55,1x60 | 55,55,60')
    ap.add_argument('--count', type=int, default=8, help='barb seats when one bonus is given (default 8)')
    ap.add_argument('--data', default=str(ROOT / 'data'))
    ap.add_argument('--source', choices=['github', 'local'], default='github', help='github = latest public/ratings.json on main (default)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if openskill.__version__ != '5.0.1': raise SystemExit('Requires openskill==5.0.1 (use BarbOS\\.venv)')
    where, humans, bots, seeds = load(Path(a.data), a.source)
    model = PlackettLuce()
    names = [n.strip() for n in a.humans.split(',') if n.strip()]
    if not names: raise SystemExit('no human names')
    hrows, team_h = [], []
    for n in names:
        r = find_human(n, humans)
        mu, sigma = (r['mu'], r['sigma']) if r else (NEW_MU, NEW_SIGMA)
        hrows.append(dict(name=r['names'][-1] if r else n, query=n, known=bool(r), mu=mu, sigma=sigma, os=mu - sigma, games=r['games'] if r else 0))
        team_h.append(model.rating(mu=mu, sigma=sigma, name=n))
    brows, team_b = [], []
    for b in parse_barbs(a.barbs, a.count):
        mu, sigma, note = bot_rating(b, bots, seeds)
        brows.append(dict(bonus=b, mu=mu, sigma=sigma, os=mu - sigma, note=note))
        team_b.append(model.rating(mu=mu, sigma=sigma, name=f'+{b:g}'))
    ph, pb = model.predict_win([team_h, team_b])
    res = dict(human_win=ph, barb_win=pb, humans=hrows, barbs=brows, ratings_source=where)
    if a.json: print(json.dumps(res, indent=1)); return
    print(f"Humans {ph*100:.1f}%  vs  Barbs {pb*100:.1f}%   ({len(hrows)} humans v {len(brows)} barbs; ratings: {where})")
    print('Humans:')
    for h in hrows:
        print(f"  {h['name']}: OS {h['os']:.1f}, {h['games']} games" if h['known'] else f"  {h['query']}: not in BarbOS (new-player prior mu 25, sigma 8.33)")
    rated = [h['os'] for h in hrows if h['known']]
    if rated: print(f"  avg OS {sum(rated)/len(rated):.1f} over {len(rated)} rated")
    print('Barbs:')
    seen = {}
    for b in brows: seen.setdefault(b['bonus'], [b, 0])[1] += 1
    for bonus, (b, n) in seen.items():
        print(f"  {n}x SMRTBARb +{bonus:g}: OS {b['os']:.1f} (mu {b['mu']:.2f}, sigma {b['sigma']:.2f}; {b['note']})")


if __name__ == '__main__': sys.exit(main())
