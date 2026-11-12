"""Top-25 human leaderboard (humans with >= MIN_GAMES), ranked by match rating mu-sigma,
with AI bonus levels in the same range interleaved (they take no human spot) and the
owner's select players always shown. A select player with fewer than MIN_GAMES games gets an
"as if 15 games" rating: their own mu, with sigma replaced by the median sigma of humans who
have exactly MIN_GAMES games. Writes public/leaderboard_top25.txt (Discord code block)."""
import csv, json, pathlib, statistics
ROOT = pathlib.Path(__file__).resolve().parent
MIN_GAMES = 15; TOP = 25
SELECT = json.loads((ROOT / 'select_players.json').read_text(encoding='utf8'))['players']

def main():
    rows = list(csv.DictReader((ROOT / 'public' / 'ratings.csv').open(encoding='utf-8-sig')))
    for r in rows: r['os'] = float(r['match_rating']); r['g'] = int(r['games']); r['note'] = ''
    humans = [r for r in rows if r['entity_type'] == 'human']
    sigma15 = statistics.median(float(r['sigma']) for r in humans if r['g'] == MIN_GAMES)
    by_id = {r['account_id']: r for r in humans}
    select = []
    for p in SELECT:
        r = by_id.get(str(p['account_id']))
        if not r: continue
        if r['g'] < MIN_GAMES:
            r['os'] = float(r['mu']) - sigma15; r['sigma'] = str(sigma15)
            r['note'] = f"as if {MIN_GAMES} games (real: {r['g']})"
        select.append(r)
    pool = sorted({id(r): r for r in [h for h in humans if h['g'] >= MIN_GAMES] + select}.values(), key=lambda r: -r['os'])
    for i, r in enumerate(pool, 1): r['rank'] = i
    top = pool[:TOP]; cut = top[-1]['os']
    shown = top + [r for r in select if r not in top]
    ais = [r for r in rows if r['entity_type'] != 'human' and r['os'] >= cut]
    lines = [f"{'#':>3}  {'Player':<22} {'OS':>6} {'mu':>6} {'sigma':>5} {'G':>4} {'W-L':>7}"]
    for r in sorted(shown + ais, key=lambda r: -r['os']):
        ai = r['entity_type'] != 'human'
        if not ai and r['rank'] == TOP + 1 or (not ai and r['rank'] > TOP and lines[-1] != '  ...' and all(x['rank'] != r['rank'] - 1 for x in shown)):
            lines.append('  ...')
        name = r['name'] + (' (AI)' if ai else '') + (' *' if r['note'] else '')
        lines.append(f"{'' if ai else r['rank']:>3}  {name[:22]:<22} {r['os']:6.2f} {float(r['mu']):6.2f} {float(r['sigma']):5.2f} {r['g']:>4} {r['wins'] + '-' + r['losses']:>7}")
    foot = [f"* {r['name']}: {r['note']} (sigma {sigma15:.2f} = median of {MIN_GAMES}-game players)" for r in select if r['note']]
    text = '```\n' + '\n'.join(lines + ([''] + foot if foot else [])) + '\n```\n'
    (ROOT / 'public' / 'leaderboard_top25.txt').write_text(text, encoding='utf8')
    print(text)

if __name__ == '__main__': main()
