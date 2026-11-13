"""Merge extra match files into BarbOS data/matches.json (dedupe on match_id, merge sources,
sort by start time). Also appends scan rows to scan_manifest.json. Usage: merge_matches.py label file [file...]"""
import sys, json, gzip, pathlib, collections, datetime as dt
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import barbos
data = pathlib.Path(__file__).resolve().parent / 'data'
label = sys.argv[1]
ds = json.loads((data/'matches.json').read_text(encoding='utf8'))
mf = json.loads((data/'scan_manifest.json').read_text(encoding='utf8'))
by_id = {m['match_id']: m for m in ds['matches']}
known_paths = {r['path'] for r in mf['files']}
added = merged_sources = 0
reviews = json.loads((data/'admin_reviews.json').read_text(encoding='utf8'))
for f in sys.argv[2:]:
    fp = pathlib.Path(f)  # .json or .json.gz (sync watcher hand-off files)
    extra = json.loads(gzip.open(fp, 'rt', encoding='utf8').read() if fp.suffix == '.gz' else fp.read_text(encoding='utf8'))
    for m in extra['matches']:
        prev = by_id.get(m['match_id'])
        if prev is None:
            if m['match_id'] in reviews: m['review'].update(reviews[m['match_id']])
            by_id[m['match_id']] = m; added += 1
        else:
            have = {s.get('sha256') or s['path'] for s in prev['sources']}
            for s in m['sources']:
                if (s.get('sha256') or s['path']) not in have:
                    prev['sources'].append(s); merged_sources += 1
                    if prev['observed_outcome']['result'] != m['observed_outcome']['result'] and 'duplicate_recording_outcome_disagreement' not in prev['automatic_flags']:
                        prev['automatic_flags'].append('duplicate_recording_outcome_disagreement')
    key = lambda r: (r.get('machine', 'VENGEANCE'), r['path'])  # both PCs use the same demos path
    rows = {key(r): r for r in mf['files']}
    for r in extra.get('files', []): rows[key(r)] = r  # newer scan wins (e.g. a once-live recording)
    mf['files'] = sorted(rows.values(), key=lambda r: r['path'])
ms = sorted(by_id.values(), key=lambda m: (m['started_at_utc'], m['match_id']))
md = ds['metadata']
md['generated_at'] = dt.datetime.now(barbos.TZ).isoformat()
md.setdefault('merges', []).append(dict(label=label, at=md['generated_at'], files=sys.argv[2:], added=added, merged_duplicate_sources=merged_sources))
md['unique_matches'] = len(ms)
md['source_file_count'] = len(mf['files'])
md['scan_counts'] = dict(collections.Counter(r['status'] for r in mf['files']))
md['candidate_recordings'] = md['scan_counts'].get('selected', 0)
md['duplicate_recordings'] = sum(len(m['sources']) for m in ms) - len(ms)
md['packet_errors'] = sum(r.get('packet_parse') == 'error' for r in mf['files'])
md['compression_integrity_errors'] = sum(bool(m.get('compression_error')) for m in ms)
mf['metadata'] = md
barbos.dump(data/'matches.json', dict(metadata=md, matches=ms))
barbos.dump(data/'scan_manifest.json', mf)
print(f'{label}: added {added}, merged duplicate sources {merged_sources}, total {len(ms)}')
