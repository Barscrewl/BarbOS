"""Auditable BAR demo extraction and anchored OpenSkill 5.0.1 replay."""
from __future__ import annotations
import argparse, collections, concurrent.futures, csv, datetime as dt, gzip, hashlib
import importlib.metadata, io, json, math, pathlib, re, struct, sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
DEMOS = pathlib.Path(r'C:\Users\artib\AppData\Local\Programs\Beyond-All-Reason\data\demos')
HEADER = struct.Struct('<16sii256s16sQ12i')
TZ = ZoneInfo('America/Los_Angeles')
CUTOFF = dt.datetime(2026,9,15,tzinfo=TZ)
STOP = re.compile(r'(?i)(?:!\s*(?:stop|cv\s+stop|callvote\s+stop)\b|\b(?:stop(?:ping|ped)?|abort(?:ed|ing)?)\s+(?:the\s+)?(?:game|match)\b|\b(?:game|match)\s+(?:was\s+)?(?:stopped|aborted)\b)')
SENSITIVE = re.compile(r'(?i)password|passwd|token|secret|hashcode')

def dump(path, value):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)

def tdf(text):
    """Parse nested startscript sections; values can include [names] and JSON."""
    pos=0
    def section(expect_close=False):
        nonlocal pos
        out={}
        while pos<len(text):
            m=re.match(r'\s+',text[pos:])
            if m:pos+=m.end();continue
            if text.startswith('//',pos):
                end=text.find('\n',pos);pos=len(text) if end<0 else end+1;continue
            if text[pos]=='}':
                if not expect_close:raise ValueError('unexpected closing brace')
                pos+=1;return out
            if text[pos]=='[':
                end=text.index(']',pos);key=text[pos+1:end].lower();pos=end+1
                while pos<len(text) and text[pos].isspace():pos+=1
                if text[pos]!='{':raise ValueError('missing section opening brace')
                pos+=1;out[key]=section(True)
            else:
                end=text.index('=',pos);key=text[pos:end].strip().lower();pos=end+1
                end=text.index(';',pos);value=text[pos:end].strip();pos=end+1
                out[key]='[REDACTED]' if SENSITIVE.search(key) else value
        if expect_close:raise ValueError('unclosed section')
        return out
    result=section()
    return result['game']

def number(v,default=None):
    try:return float(v)
    except (ValueError,TypeError):return default

def header_script(path):
    with gzip.open(path,'rb') as f:
        raw=f.read(HEADER.size)
        if len(raw)!=HEADER.size:raise ValueError('short demo header')
        h=HEADER.unpack(raw)
        if h[0]!=b'spring demofile\0' or h[1]!=5:raise ValueError('unsupported demo magic/version')
        if h[2]<HEADER.size or not 0<=h[6]<=10_000_000:raise ValueError('invalid header/script size')
        f.read(h[2]-HEADER.size)
        script=f.read(h[6])
        if len(script)!=h[6]:raise ValueError('truncated startscript')
    return h,script

def roster(g):
    players=[];spectators=[];ais=[];teams={}
    for k,v in g.items():
        if re.fullmatch(r'team\d+',k):teams[int(k[4:])]=v
    def seat(v):
        tid=int(v['team']);t=teams[tid]
        return dict(team_id=tid,ally_team_id=int(t['allyteam']),bonus_percent=number(t.get('handicap','0')),faction=t.get('side'),team_settings=t)
    for k,v in g.items():
        if re.fullmatch(r'player\d+',k):
            p=dict(player_id=int(k[6:]),account_id=v.get('accountid'),name=v.get('name'),lobby_match_rating=number(re.sub(r'[\[\]() ]','',v.get('skill',''))),lobby_sigma=number(v.get('skilluncertainty')),settings=v)
            p['rating_key']='human:'+str(p['account_id']) if p['account_id'] else 'human-name:'+p['name'].casefold()
            if v.get('spectator','0')=='1':spectators.append(p)
            else:p.update(seat(v));players.append(p)
        elif re.fullmatch(r'ai\d+',k):
            a=dict(ai_id=int(k[2:]),name=v.get('name'),short_name=v.get('shortname'),version=v.get('version'),options=v.get('options',{}),host_player_id=v.get('host'),settings=v)
            a.update(seat(v));a['rating_key']='ai:'+str(a['short_name'])+':bonus:'+format(a['bonus_percent'],'g');ais.append(a)
    return sorted(players,key=lambda p:p['player_id']),sorted(ais,key=lambda a:a['ai_id']),spectators

def scan_one(path):
    row={'path':str(path),'bytes':path.stat().st_size,'mtime_ns':path.stat().st_mtime_ns}
    if not row['bytes']:return row|{'status':'empty_or_live_recording'}
    try:
        h,s=header_script(path)
        stamp=dt.datetime.fromtimestamp(h[5],dt.timezone.utc)
        row.update(started_at_utc=stamp.isoformat(),started_at_local=stamp.astimezone(TZ).isoformat(),game_id=h[4].hex())
        if stamp<CUTOFF:return row|{'status':'before_cutoff'}
        g=tdf(s.decode('utf8',errors='replace'));players,ais,specs=roster(g)
        by_ally=collections.Counter(a['ally_team_id'] for a in ais if (a['short_name'] or '').casefold()=='smrtbarb')
        selected=sorted(a for a,n in by_ally.items() if n==8)
        row.update(ai_counts_by_ally=dict(by_ally),map=g.get('mapname'))
        if not selected:return row|{'status':'not_eight_smrtbarbs_on_one_team'}
        return row|{'status':'selected','ai_ally_team_ids':selected}
    except Exception as e:return row|{'status':'scan_error','error':f'{type(e).__name__}: {e}'}

def parse_match(row):
    path=pathlib.Path(row['path']);h,s=header_script(path);g=tdf(s.decode('utf8',errors='replace'))
    players,ais,spectators=roster(g);blob=path.read_bytes();compression_error=None
    try:data=gzip.decompress(blob)
    except (EOFError,gzip.BadGzipFile) as exc:
        compression_error=f'{type(exc).__name__}: {exc}'
        blocks=[]
        with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
            try:
                while block:=stream.read(65536):blocks.append(block)
            except (EOFError,gzip.BadGzipFile):pass
        data=b''.join(blocks)
        if len(data)<h[2]+h[6]:raise ValueError('compression damage prevents startscript recovery')
    offset=h[2]+h[6];end=offset+h[7] if h[7] else len(data)
    issues=['compression_integrity_error'] if compression_error else [];events=[];chat=[];winner_reports=[];frame=0;counts=collections.Counter();started=False;last_time=0
    if not h[7]:issues.append('unfinalized_demo_stream')
    if end>len(data):issues.append('truncated_demo_stream');end=len(data)
    while offset<end:
        if offset+8>end:issues.append('truncated_chunk_header');break
        time,n=struct.unpack_from('<fI',data,offset);offset+=8
        if n<1 or offset+n>end:issues.append('invalid_chunk_length');break
        p=memoryview(data)[offset:offset+n];offset+=n;cmd=p[0];counts[cmd]+=1;last_time=time
        if cmd==1:
            frame=struct.unpack_from('<i',p,1)[0]
        elif cmd==2:frame+=1
        elif cmd==4 and struct.unpack_from('<I',p,1)[0]==0:started=True
        base=dict(demo_seconds=round(time,4),game_seconds=round(frame/30,4),frame=frame)
        if cmd in (7,35):
            off=4 if cmd==7 else 3
            chat.append(base|{'kind':'chat' if cmd==7 else 'system','player_id':p[2],'destination':p[3] if cmd==7 else None,'text':bytes(p[off:]).rstrip(b'\0').decode('utf8','replace')})
        elif cmd==30:
            if len(p)<3 or p[1]!=len(p):issues.append('invalid_gameover_packet');continue
            e=base|{'kind':'gameover','reporter_player_id':p[2],'winning_ally_team_ids':list(p[3:])};events.append(e);winner_reports.append(e)
        elif cmd==51:
            events.append(base|{'kind':'team','player_id':p[1],'action':{1:'giveaway',2:'resign',3:'join_team',4:'team_died'}.get(p[2],str(p[2])),'parameter_1':p[3],'parameter_2':p[4] if len(p)>4 else None})
        elif cmd==54:
            parts=bytes(p[7:]).rstrip(b'\0').decode('utf8','replace').split('\0',1)
            events.append(base|{'kind':'command','player_id':struct.unpack_from('<i',p,3)[0],'command':parts[0],'extra':parts[1] if len(parts)>1 else ''})
        elif cmd==39:
            events.append(base|{'kind':'player_left','player_id':p[1],'reason_code':p[2]})
        elif cmd==3:
            events.append(base|{'kind':'quit','reason':bytes(p[2:]).rstrip(b'\0').decode('utf8','replace')})
    trailer_start=h[2]+h[6]+h[7]
    trailer=list(data[trailer_start:trailer_start+h[17]]) if h[7] and h[17] else []
    reports={tuple(sorted(e['winning_ally_team_ids'])) for e in winner_reports}
    if len(reports)>1:issues.append('conflicting_gameover_reports')
    packet_winners=list(next(iter(reports))) if len(reports)==1 else []
    if trailer and reports and tuple(sorted(trailer)) not in reports:issues.append('trailer_packet_winner_disagreement')
    winners=packet_winners if reports else trailer
    if not winners:issues.append('no_decisive_winner')
    if not started:issues.append('no_startplaying_packet')
    if row['bytes']!=path.stat().st_size or row['mtime_ns']!=path.stat().st_mtime_ns:issues.append('file_changed_during_scan')
    signals=[c for c in chat if STOP.search(c['text'])]
    signals += [e for e in events if e['kind']=='command' and e['command'].lower() in ('stop','cheat','godmode','nocost') and e.get('extra','') not in ('0','off')]
    if signals:issues.append('stop_or_cheat_signal_requires_review')
    ai_ally=row['ai_ally_team_ids'][0];human_allies=sorted({p['ally_team_id'] for p in players})
    if len(row['ai_ally_team_ids'])!=1 or len(human_allies)!=1 or ai_ally in human_allies:issues.append('unsupported_team_layout')
    if len(ais)!=8:issues.append('additional_ai_participants')
    if any(p['bonus_percent']!=0 for p in players):issues.append('human_handicap_requires_model')
    if len({p['rating_key'] for p in players})!=len(players):issues.append('duplicate_human_identity')
    if len(winners)!=1 or (winners and winners[0] not in [ai_ally]+human_allies):issues.append('nondecisive_or_unknown_winner')
    if len({p['team_id'] for p in players})!=len(players):issues.append('shared_human_team_requires_model')
    ai_win=ai_ally in winners
    result='ai_win' if len(winners)==1 and ai_win else 'human_win' if len(winners)==1 and winners[0] in human_allies else 'unknown'
    cache_path=path.with_suffix(path.suffix+'.cache');cache=None
    if cache_path.exists():
        try:cache=json.loads(cache_path.read_text(encoding='utf8'))
        except (ValueError,UnicodeError):issues.append('unreadable_lobby_cache')
    if cache and sorted(cache.get('winningAllyTeamIds',[]))!=sorted(winners):issues.append('cache_winner_disagreement')
    ident=h[4].hex()
    if not ident.strip('0'):ident='sha256:'+hashlib.sha256(blob).hexdigest()
    return dict(match_id=ident,server_match_id=g.get('server_match_id'),started_at_utc=row['started_at_utc'],started_at_local=row['started_at_local'],map=g.get('mapname'),game=g.get('gametype'),engine=h[3].split(b'\0')[0].decode('utf8','replace'),duration_seconds=h[8],wallclock_seconds=h[9],last_recorded_frame=frame,last_demo_seconds=last_time,human_ally_team_ids=human_allies,ai_ally_team_id=ai_ally,players=players,ais=ais,spectators=spectators,observed_outcome=dict(result=result,winning_ally_team_ids=winners,packet_reports=winner_reports,trailer_winning_ally_team_ids=trailer),review=dict(admin_thinks_cheated=None,exclude_from_processing=False,include_despite_automatic_flags=False,override_result=None,override_termination=None,reviewed_by=None,reviewed_at=None,notes=''),automatic_flags=sorted(set(issues)),review_signals=signals,events=events,chat=chat,settings={k:v for k,v in g.items() if not re.fullmatch(r'(?:player|ai|team)\d+',k)},sources=[dict(path=str(path),bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),cache_path=str(cache_path) if cache else None,cache=cache)],compression_error=compression_error,observed_termination='stop_or_cheat_signal' if signals else 'gameover' if winner_reports else 'unknown',header=dict(version=h[1],header_size=h[2],script_bytes=h[6],stream_bytes=h[7],num_players=h[10],num_teams=h[13],winner_trailer_bytes=h[17]),packet_counts=dict(counts))

def extract(args):
    paths=sorted(args.demos.glob('*.sdfz'));print(f'Scanning {len(paths)} replay files',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(scan_one,paths))
    selected=[r for r in rows if r['status']=='selected'];print(f'Found {len(selected)} candidate recordings; parsing packets',flush=True)
    matches=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(parse_match,r):r for r in selected}
        for i,f in enumerate(concurrent.futures.as_completed(jobs),1):
            row=jobs[f]
            try:matches.append(f.result());row['packet_parse']='ok'
            except Exception as e:row['packet_parse']='error';row['error']=f'{type(e).__name__}: {e}'
            if i%20==0 or i==len(jobs):print(f'Parsed {i}/{len(jobs)}',flush=True)
    by_id={}
    for m in sorted(matches,key=lambda m:m['sources'][0]['path']):
        ident=m['match_id']
        if ident in by_id:
            previous=by_id[ident]
            if previous['observed_outcome']['result']!=m['observed_outcome']['result']:
                previous['automatic_flags'].append('duplicate_recording_outcome_disagreement')
            previous['sources'].extend(m['sources'])
        else:by_id[ident]=m
    matches=sorted(by_id.values(),key=lambda m:(m['started_at_utc'],m['match_id']))
    decisions_path=args.output/'admin_reviews.json'
    decisions=json.loads(decisions_path.read_text(encoding='utf8')) if decisions_path.exists() else {}
    for m in matches:
        if m['match_id'] in decisions:m['review'].update(decisions[m['match_id']])
    now=dt.datetime.now(TZ).isoformat()
    metadata=dict(schema_version=1,generated_at=now,cutoff=CUTOFF.isoformat(),source_directory=str(args.demos),selection='Exactly 8 shortname=SMRTBARb on the same ally team, determined from embedded startscript; other layouts retained but may be unrated.',source_file_count=len(paths),candidate_recordings=len(selected),unique_matches=len(matches),scan_counts=dict(collections.Counter(r['status'] for r in rows)),packet_errors=sum(r.get('packet_parse')=='error' for r in rows),duplicate_recordings=sum(len(m['sources']) for m in matches)-len(matches),compression_integrity_errors=sum(bool(m.get('compression_error')) for m in matches),shared_discussion_status='Only preview metadata accessible; discussion content unavailable')
    dump(args.output/'matches.json',dict(metadata=metadata,matches=matches));dump(args.output/'scan_manifest.json',dict(metadata=metadata,files=rows))
    if not decisions_path.exists():dump(decisions_path,{})
    print(json.dumps(metadata,indent=2),flush=True)

def effective(m,decisions):
    review=m['review']|decisions.get(m['match_id'],{})
    if review['override_result'] not in (None,'human_win','ai_win','unknown'):raise ValueError('Invalid result override for '+m['match_id'])
    flags=list(m['automatic_flags'])
    if review['exclude_from_processing']:return None,['admin_excluded'],review
    termination=review.get('override_termination')
    if termination not in (None,'human_resign','ai_resign','stop','unknown'):raise ValueError('Invalid termination override for '+m['match_id'])
    implied={'human_resign':'ai_win','ai_resign':'human_win'}.get(termination)
    if implied and review['override_result'] and implied!=review['override_result']:raise ValueError('Conflicting result and termination overrides for '+m['match_id'])
    corrected=review['override_result'] or implied
    result=corrected or m['observed_outcome']['result']
    if termination=='stop':flags.append('admin_confirmed_stop')
    if review['admin_thinks_cheated'] is True and not corrected:flags.append('admin_cheated_without_corrected_outcome')
    if corrected in ('human_win','ai_win'):
        flags=[f for f in flags if f not in ('no_decisive_winner','nondecisive_or_unknown_winner','conflicting_gameover_reports','trailer_packet_winner_disagreement','cache_winner_disagreement','stop_or_cheat_signal_requires_review')]
    if review['include_despite_automatic_flags']:
        flags=[f for f in flags if f not in ('stop_or_cheat_signal_requires_review','cache_winner_disagreement')]
    if result not in ('human_win','ai_win'):flags.append('unknown_result')
    return result,sorted(set(flags)),review

def rate_calibration(args):
    import openskill
    from openskill.models import PlackettLuce
    if openskill.__version__!='5.0.1':raise ValueError('Requires openskill==5.0.1')
    source=args.output/'matches.json';dataset=json.loads(source.read_text(encoding='utf8'))
    decisions_path=args.output/'admin_reviews.json';decisions=json.loads(decisions_path.read_text(encoding='utf8'))
    model=PlackettLuce();state={};records={};history=[];skipped=[];queue=[];graph=collections.defaultdict(set)
    anchor='ai:SMRTBARb:bonus:50'
    def get(key,name):
        if key not in state:
            state[key]=model.rating(mu=21,sigma=1,name=key) if key==anchor else model.rating(name=key)
            records[key]=dict(key=key,names=[],games=0,wins=0,losses=0,seat_appearances=0,first_match=None,last_match=None)
        if name not in records[key]['names']:records[key]['names'].append(name)
        r=state[key]
        return model.rating(mu=r.mu,sigma=r.sigma,name=key)
    for m in sorted(dataset['matches'],key=lambda m:(m['started_at_utc'],m['match_id'])):
        result,reasons,review=effective(m,decisions)
        if reasons:
            entry=dict(match_id=m['match_id'],started_at_local=m['started_at_local'],map=m['map'],observed_result=m['observed_outcome']['result'],reasons=reasons,review_signals=m['review_signals'],review=review)
            skipped.append(entry);queue.append(entry);continue
        humans=m['players'];ais=m['ais'];seats=[humans,ais]
        teams=[[get(p['rating_key'],p['name']) for p in team] for team in seats]
        keys={p['rating_key'] for team in seats for p in team}
        first=next(iter(keys))
        for key in keys:graph[first].add(key);graph[key].add(first)
        ranks=[1,2] if result=='human_win' else [2,1]
        before={r.name:(r.mu,r.sigma) for t in teams for r in t}
        predicted=model.predict_win(teams)
        updated=model.rate(teams,ranks=ranks)
        grouped=collections.defaultdict(list);counts=collections.Counter()
        for team,out in zip(seats,updated):
            for p,r in zip(team,out):grouped[p['rating_key']].append(r);counts[p['rating_key']]+=1
        deltas=[]
        for key,rs in grouped.items():
            if key==anchor:state[key]=model.rating(mu=21,sigma=1,name=key)
            else:state[key]=model.rating(mu=sum(r.mu for r in rs)/len(rs),sigma=sum(r.sigma for r in rs)/len(rs),name=key)
            r=state[key];rec=records[key];rec['games']+=1;rec['seat_appearances']+=counts[key]
            win=(key.startswith('human:') or key.startswith('human-name:'))==(result=='human_win')
            rec['wins']+=int(win);rec['losses']+=int(not win);rec['first_match']=rec['first_match'] or m['started_at_utc'];rec['last_match']=m['started_at_utc']
            deltas.append(dict(key=key,before_mu=before[key][0],before_sigma=before[key][1],after_mu=r.mu,after_sigma=r.sigma,mu_delta=r.mu-before[key][0],seat_count=counts[key],fixed=key==anchor))
        assert anchor not in state or (state[anchor].mu,state[anchor].sigma)==(21,1)
        history.append(dict(match_id=m['match_id'],started_at_utc=m['started_at_utc'],result=result,ranks=ranks,predicted_human_win_probability=predicted[0],ratings=deltas,review=review))
    # Always publish the anchor, even if no eligible +50 matches are available.
    get(anchor,'SMRTBARb +50')
    anchored=set();pending=[anchor]
    while pending:
        key=pending.pop()
        if key in anchored:continue
        anchored.add(key);pending.extend(graph[key]-anchored)
    ratings=[]
    for key,r in state.items():
        ratings.append(records[key]|dict(mu=r.mu,sigma=r.sigma,match_rating=r.mu-r.sigma,leaderboard_rating=r.mu-3*r.sigma,fixed=key==anchor,connected_to_anchor=key in anchored))
    ratings.sort(key=lambda r:r['match_rating'],reverse=True)
    metadata=dict(generated_at=dt.datetime.now(TZ).isoformat(),openskill_version=openskill.__version__,model='PlackettLuce',parameters=dict(mu=25,sigma=25/3,beta=25/6,tau=25/300,kappa=0.0001),anchor=dict(key=anchor,mu=21,sigma=1,match_rating=20,per_ai_seat=True),human_initial_prior=dict(mu=25,sigma=25/3),ai_other_bonus_prior=dict(mu=25,sigma=25/3),shared_ai_parameter_update='Average posterior mu and sigma across the separate AI seats of each bonus category, once per match; fixed +50 posteriors discarded. Tied-seat approximation, not an exact constrained Bayesian posterior.',ai_pooling='By shortname and bonus across maps, profiles, versions and calendar time; replay does not supply AI binary hashes.',rating_scale=dict(match='mu - sigma',leaderboard='mu - 3*sigma'),matches_rated=len(history),matches_excluded=len(skipped),entities_disconnected_from_anchor=sum(not r['connected_to_anchor'] for r in ratings),human_count=sum(r['key'].startswith('human') for r in ratings),dataset_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),reviews_sha256=hashlib.sha256(decisions_path.read_bytes()).hexdigest())
    dump(args.output/'ratings.json',dict(metadata=metadata,ratings=ratings));dump(args.output/'rating_history.json',dict(metadata=metadata,matches=history,excluded=skipped));dump(args.output/'review_queue.json',queue)
    with (args.output/'ratings.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['key','names','mu','sigma','match_rating','leaderboard_rating','games','wins','losses','seat_appearances','fixed'];writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for r in ratings:writer.writerow(r|{'names':' | '.join(r['names'])})
    print(json.dumps(metadata,indent=2),flush=True)

def rate(args):
    from fixed_ratings import run
    run(args)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['extract','rate','all']);parser.add_argument('--demos',type=pathlib.Path,default=DEMOS);parser.add_argument('--output',type=pathlib.Path,default=ROOT/'data');parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.command in ('extract','all'):extract(args)
    if args.command in ('rate','all'):rate(args)
if __name__=='__main__':main()
