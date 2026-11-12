"""Scan demos newer than a given UTC filename prefix with barbos.scan_one/parse_match;
write new matches + scan rows to an output JSON (does not touch data/)."""
import sys, json, pathlib, concurrent.futures, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import barbos

def main():
    demos = pathlib.Path(sys.argv[1]); since = sys.argv[2]; out = pathlib.Path(sys.argv[3])
    paths = sorted(p for p in demos.glob('*.sdfz') if p.name >= since)
    print(f'{len(paths)} files with name >= {since}', flush=True)
    with concurrent.futures.ThreadPoolExecutor(8) as pool: rows = list(pool.map(barbos.scan_one, paths))
    sel = [r for r in rows if r['status'] == 'selected']
    print(collections.Counter(r['status'] for r in rows), flush=True)
    matches = []
    with concurrent.futures.ProcessPoolExecutor(6) as pool:
        jobs = {pool.submit(barbos.parse_match, r): r for r in sel}
        for f in concurrent.futures.as_completed(jobs):
            r = jobs[f]
            try: matches.append(f.result()); r['packet_parse'] = 'ok'
            except Exception as e: r['packet_parse'] = 'error'; r['error'] = f'{type(e).__name__}: {e}'
    matches.sort(key=lambda m: (m['started_at_utc'], m['match_id']))
    barbos.dump(out, dict(metadata=dict(source_directory=str(demos), since_filename=since, files=len(paths)), matches=matches, files=rows))
    print(len(matches), 'matches;', sum(r.get('packet_parse') == 'error' for r in rows), 'parse errors')

if __name__ == '__main__': main()
