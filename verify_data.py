"""Cross-check all artifacts and the snapshot against the source replay inventory."""
import collections,csv,datetime as dt,hashlib,json,math,pathlib
import barbos
p=barbos.ROOT/'data'
def read(name):return json.loads((p/name).read_text(encoding='utf8'))
d=read('matches.json');h=read('rating_history.json');r=read('ratings.json');mf=read('scan_manifest.json')
ids=[m['match_id'] for m in d['matches']];assert len(ids)==len(set(ids))==d['metadata']['unique_matches']
selected=[x for x in mf['files'] if x['status']=='selected'];assert len(selected)==sum(len(m['sources']) for m in d['matches'])
assert len(h['matches'])+len(h['excluded'])==len(d['matches'])
assert len({m['match_id'] for m in h['matches']+h['excluded']})==len(ids)
assert not ({m['match_id'] for m in h['matches']}&{m['match_id'] for m in h['excluded']})
for m in d['matches']:
    assert dt.datetime.fromisoformat(m['started_at_utc'])>=barbos.CUTOFF
    assert collections.Counter(a['ally_team_id'] for a in m['ais'] if a['short_name'].casefold()=='smrtbarb')[m['ai_ally_team_id']]==8
    assert all(m['sources'])
anchor=next(x for x in r['ratings'] if x['key']==r['metadata']['anchor']['key']);assert (anchor['mu'],anchor['sigma'],anchor['match_rating'])==(21,1,20)
for x in r['ratings']:
    assert all(math.isfinite(x[k]) for k in ('mu','sigma','match_rating','leaderboard_rating'))
    assert x['sigma']>0 and x['wins']+x['losses']==x['games']
for m in h['matches']:
    for rating in m['ratings']:
        if rating['fixed']:
            assert rating['before_mu']==rating['after_mu']
            assert rating['before_sigma']==rating['after_sigma']
            if rating['key']==r['metadata']['anchor']['key']:assert (rating['before_mu'],rating['before_sigma'],rating['after_mu'],rating['after_sigma'])==(21,1,21,1)
assert r['metadata']['dataset_sha256']==hashlib.sha256((p/'matches.json').read_bytes()).hexdigest()
corrupt={m['match_id'] for m in d['matches'] if m.get('compression_error')};assert len(corrupt)==d['metadata']['compression_integrity_errors']
assert corrupt<={m['match_id'] for m in h['excluded']}
# Rows scanned on another machine (e.g. GreenParrots) are not on this PC's demo folder.
local=[x for x in mf['files'] if x.get('machine','VENGEANCE')=='VENGEANCE']
current={str(x) for x in barbos.DEMOS.glob('*.sdfz')};snapshot={x['path'] for x in local}
changed=[x['path'] for x in selected if x.get('machine','VENGEANCE')=='VENGEANCE' and (pathlib.Path(x['path']).stat().st_size!=x['bytes'] or pathlib.Path(x['path']).stat().st_mtime_ns!=x['mtime_ns'])]
assert not changed,changed
# Rating replay must be deterministic apart from its generation timestamp.
args=type('Args',(),{'output':p})();barbos.rate(args)
r2=read('ratings.json');h2=read('rating_history.json')
assert r['ratings']==r2['ratings'];assert h['matches']==h2['matches'];assert h['excluded']==h2['excluded']
import report
report.generate(p)
with (p/'matches_index.csv').open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==len(ids)
result=dict(validated_at=dt.datetime.now(barbos.TZ).isoformat(),status='PASS',tests=['complete selected-source coverage','one entry per unique match','date and eight-SMRTBARb selection','rated/excluded partition','finite ratings and game counts','all bot seeds fixed before and after every match, +50 exactly 21/1','all four corrupt matches retained and excluded','source inventory snapshot and unchanged qualifying files','deterministic full chronological rerating','CSV match coverage'],source_files_added_since_scan=sorted(current-snapshot),source_files_removed_since_scan=sorted(snapshot-current),changed_qualifying_sources=changed,artifact_sha256={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(p.iterdir()) if x.is_file() and x.name!='validation.json'})
barbos.dump(p/'validation.json',result)
print(json.dumps(result,indent=2))
