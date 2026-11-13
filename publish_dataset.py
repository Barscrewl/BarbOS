"""Write the public copy data/matches.json.gz: the local data/matches.json with every
match's `chat` field removed. Deterministic gzip (mtime 0), so unchanged data gives the
same bytes. Refuses to write if any chat survives."""
import gzip, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent


def main():
    d = json.loads((ROOT / 'data' / 'matches.json').read_text(encoding='utf8'))
    for m in d['matches']: m.pop('chat', None)
    d['metadata']['published_copy'] = 'chat field removed for the public repository; full local copy keeps it'
    text = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
    # review_signals keep their stop-vote lines (kind "chat"), as in every earlier public copy; only the chat field goes.
    assert '"chat":' not in text, 'chat field survived'
    out = ROOT / 'data' / 'matches.json.gz'; tmp = out.with_name(out.name + '.tmp')
    with open(tmp, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as f: f.write(text.encode('utf8'))
    tmp.replace(out)
    print(f'published {len(d["matches"])} matches without chat -> {out.name} ({out.stat().st_size:,} bytes)')


if __name__ == '__main__': main()
