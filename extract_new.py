"""Extract replays this machine has not processed yet (for the sync watcher, sync/barbos_sync.ps1).

  extract_new.py scan --machine NAME --state STATE.json --out OUT.json.gz [--demos DIR] [--settle 120]
      Writes new matches + scan rows (sources[].machine and files[].machine = NAME) to OUT
      (gzip JSON; chat included, so OUT must never go to the public repo). Prints a JSON
      line {"files": n, "matches": n, "errors": n}. Writes nothing when there is no new file.
  extract_new.py mark --state STATE.json OUT.json.gz [...]
      Records the scan rows of OUT files as processed (call after the hand-off succeeded).

A file is new when its (bytes, mtime) differ from the state row. Zero-byte files (a game
still recording) and files modified in the last --settle seconds are left for a later run.
On VENGEANCE the state is data/scan_manifest.json itself (merge_matches.py updates it)."""
import argparse, collections, concurrent.futures, gzip, json, os, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import barbos


def load(path):
    path = pathlib.Path(path)
    if not path.exists(): return {}
    data = json.loads((gzip.open(path, 'rt', encoding='utf8') if path.suffix == '.gz' else path.open(encoding='utf8')).read())
    return data


def state_rows(path, machine):
    data = load(path)
    rows = data.get('files', []) if isinstance(data, dict) else []
    return {r['path']: (r['bytes'], r['mtime_ns']) for r in rows if r.get('machine', 'VENGEANCE') == machine}


def scan(a):
    done = state_rows(a.state, a.machine)
    now = time.time(); paths = []
    for p in sorted(pathlib.Path(a.demos).glob('*.sdfz')):
        try: st = p.stat()
        except OSError: continue
        if not st.st_size or now - st.st_mtime < a.settle: continue
        if done.get(str(p)) == (st.st_size, st.st_mtime_ns): continue
        paths.append(p)
    if not paths:
        print(json.dumps(dict(files=0, matches=0, errors=0))); return
    with concurrent.futures.ThreadPoolExecutor(a.workers) as pool: rows = list(pool.map(barbos.scan_one, paths))
    sel = [r for r in rows if r['status'] == 'selected']; matches = []
    with concurrent.futures.ProcessPoolExecutor(max(1, a.workers // 2)) as pool:
        jobs = {pool.submit(barbos.parse_match, r): r for r in sel}
        for f in concurrent.futures.as_completed(jobs):
            r = jobs[f]
            try: matches.append(f.result()); r['packet_parse'] = 'ok'
            except Exception as e: r['packet_parse'] = 'error'; r['error'] = f'{type(e).__name__}: {e}'
    for r in rows: r['machine'] = a.machine
    for m in matches:
        for s in m['sources']: s['machine'] = a.machine
    matches.sort(key=lambda m: (m['started_at_utc'], m['match_id']))
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    doc = dict(metadata=dict(machine=a.machine, source_directory=str(a.demos), files=len(paths),
                             scan_counts=dict(collections.Counter(r['status'] for r in rows)),
                             extracted_at=barbos.dt.datetime.now(barbos.TZ).isoformat()),
               matches=matches, files=rows)
    tmp = out.with_name(out.name + '.tmp')
    with gzip.open(tmp, 'wt', encoding='utf8') as f: json.dump(doc, f, ensure_ascii=False)
    os.replace(tmp, out)
    print(json.dumps(dict(files=len(paths), matches=len(matches), errors=sum(r.get('packet_parse') == 'error' for r in rows))))


def mark(a):
    st = load(a.state) or {'files': []}
    rows = {(r.get('machine', 'VENGEANCE'), r['path']): r for r in st['files']}
    for f in a.outs:
        for r in load(f).get('files', []):
            rows[(r['machine'], r['path'])] = dict(path=r['path'], bytes=r['bytes'], mtime_ns=r['mtime_ns'], machine=r['machine'], status=r['status'])
    st['files'] = sorted(rows.values(), key=lambda r: (r['machine'], r['path']))
    tmp = pathlib.Path(str(a.state) + '.tmp'); tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf8'); os.replace(tmp, a.state)
    print(f'marked; state has {len(rows)} files')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan'); s.add_argument('--machine', required=True); s.add_argument('--state', required=True)
    s.add_argument('--out', required=True); s.add_argument('--demos', default=str(barbos.DEMOS))
    s.add_argument('--settle', type=int, default=120); s.add_argument('--workers', type=int, default=4)
    m = sub.add_parser('mark'); m.add_argument('--state', required=True); m.add_argument('outs', nargs='+')
    a = ap.parse_args(); (scan if a.cmd == 'scan' else mark)(a)


if __name__ == '__main__': main()
