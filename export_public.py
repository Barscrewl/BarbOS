"""Publish readable rating and AI-team summaries without replay chat."""
import collections,csv,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent

def team_summary(ais):
    groups=collections.Counter((a.get('short_name','SMRTBARb'),float(a['bonus_percent']),a.get('version') or 'unknown',a.get('options',{}).get('profile') or 'unknown') for a in ais)
    composition=[]
    for (family,bonus,version,profile),count in sorted(groups.items()):
        label=f'{family} +{bonus:g}'
        if version!='unknown':label+=f' ({version})'
        if profile!='unknown':label+=f' [{profile}]'
        composition.append(dict(ai_name=family,bonus_percent=bonus,ai_version=version,profile=profile,count=count,label=label))
    bonuses={g['bonus_percent'] for g in composition}
    shared=next(iter(bonuses)) if len(bonuses)==1 else None
    label='; '.join(f"{g['count']} x {g['label']}" for g in composition)
    return dict(ai_team=label,shared_bonus_percent=shared,mixed_bonuses=len(bonuses)>1,ai_count=len(ais),composition=composition)

def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})

def generate(ratings_dir=ROOT/'data'/'varying',p=ROOT/'public'):
    """Primary lists come from the varying-bot run (data/varying); the frozen-seed run is
    exported to public/fixed_seed with generate(ROOT/'data',ROOT/'public'/'fixed_seed')."""
    p.mkdir(parents=True,exist_ok=True)
    read=lambda name,d=ROOT/'data':json.loads((d/name).read_text(encoding='utf8'))
    ratings=read('ratings.json',ratings_dir);seeds=read('bot_seeds.json')['seeds'];dataset=read('matches.json');history=read('rating_history.json',ratings_dir)
    rows=[]
    for r in ratings['ratings']:
        bot=r['key'].startswith('ai:');config=seeds[r['key']]['configuration'] if bot else {}
        label=f"{config['short_name']} +{config['bonus_percent']:g}" if bot else r['names'][-1]
        if bot and config['ai_version']!='unknown':label+=f" ({config['ai_version']})"
        if bot and config['profile']!='unknown':label+=f" [{config['profile']}]"
        row=dict(entity_type='AI bonus' if bot else 'human',name=label,bonus_percent=config.get('bonus_percent'),ai_name=config.get('short_name'),ai_version=config.get('ai_version'),profile=config.get('profile'),account_id=r['key'].split(':',1)[1] if not bot and r['key'].startswith('human:') else None,names=label if bot else ' | '.join(r['names']))
        row.update({k:r.get(k) for k in ('mu','sigma','match_rating','leaderboard_rating','games','wins','losses','fixed','seed_status')});row['seed_version']=r.get('seed_version');rows.append(row)
    write_csv(p/'ratings.csv',rows)
    write_csv(p/'ratings_by_mu.csv',sorted(rows,key=lambda r:r['mu'],reverse=True))
    write_csv(p/'ratings_by_leaderboard_rating.csv',sorted(rows,key=lambda r:r['leaderboard_rating'],reverse=True))
    write_csv(p/'ratings_over_15_games.csv',[r for r in rows if r['games']>15])
    bots=sorted((r for r in rows if r['entity_type']=='AI bonus'),key=lambda r:(r['bonus_percent'],r['ai_version'],r['profile']))
    write_csv(p/'barb_bonuses.csv',bots)
    (p/'ratings.json').write_text(json.dumps(dict(description='BarbOS PvE ratings; displayed OS=mu-sigma. AI identity uses family, bonus and configuration, never lobby instance names. AI OS is per bot, not a team total.',ratings=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    used={m['match_id'] for m in history['matches']};excluded={m['match_id']:m['reasons'] for m in history['excluded']};matches=[]
    for m in dataset['matches']:
        summary=team_summary([a for a in m['ais'] if a['ally_team_id']==m['ai_ally_team_id']])
        matches.append(dict(match_id=m['match_id'],started_at_utc=m['started_at_utc'],started_at_local=m['started_at_local'],map=m['map'],duration_seconds=m['duration_seconds'],human_count=len(m['players']),ai_team=summary['ai_team'],shared_bonus_percent=summary['shared_bonus_percent'],mixed_bonuses=summary['mixed_bonuses'],ai_count=summary['ai_count'],ai_composition=summary['composition'],observed_result=m['observed_outcome']['result'],rated=m['match_id'] in used,exclusion_reasons=' | '.join(excluded.get(m['match_id'],[]))))
    write_csv(p/'matches.csv',matches)
    assert all('SMRTBARbstable(' not in r['name'] for r in bots)
    assert next(r for r in bots if r['bonus_percent']==50)['match_rating']==20 and next(r for r in bots if r['bonus_percent']==50)['fixed']
    print(f'Published exports: {len(rows)} ratings, {len(bots)} bonus configurations, {len(matches)} match summaries')
if __name__=='__main__':
    generate()
    generate(ROOT/'data',ROOT/'public'/'fixed_seed')
