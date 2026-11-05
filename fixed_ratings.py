"""Fixed, versioned opponent seeds; persist human OpenSkill updates only."""
from __future__ import annotations
import collections,contextlib,csv,datetime as dt,hashlib,io,json,math,pathlib
import openskill
from openskill.models import PlackettLuce
import barbos

def configuration(ai):
    bonus=float(ai.get('bonus_percent',ai['rating_key'].rsplit(':',1)[1]))
    config=dict(short_name=ai.get('short_name','SMRTBARb'),ai_version=ai.get('version') or 'unknown',profile=ai.get('options',{}).get('profile') or 'unknown',bonus_percent=bonus)
    return config

def config_key(config):
    return f"ai:{config['short_name']}:version:{config['ai_version']}:profile:{config['profile']}:bonus:{config['bonus_percent']:g}"

ANCHOR_CONFIG=dict(short_name='SMRTBARb',ai_version='unknown',profile='unknown',bonus_percent=50.0)
ANCHOR=config_key(ANCHOR_CONFIG)

def build_seeds(folder,dataset,reviews):
    eligible=[m for m in sorted(dataset['matches'],key=lambda m:(m['started_at_utc'],m['match_id'])) if not barbos.effective(m,reviews)[1]]
    if not eligible:raise ValueError('No eligible matches to calibrate')
    split=max(1,int(len(eligible)*0.8));train=eligible[:split]
    # Keep all matches sharing the boundary timestamp on the training side.
    while split<len(eligible) and eligible[split]['started_at_utc']==train[-1]['started_at_utc']:
        train.append(eligible[split]);split+=1
    fit=folder/'seed_calibration_v1';fit.mkdir(exist_ok=True)
    # Preserve necessary rating inputs without duplicating all replay chat/settings.
    lite=[]
    for m in train:
        row={k:m[k] for k in ('match_id','started_at_utc','started_at_local','map','players','ais','review','automatic_flags','observed_outcome','review_signals')}
        row['ais']=[a|{'rating_key':config_key(configuration(a))} for a in m['ais']]
        # Baseline fitter has a single hard-coded anchor; retain its legacy key
        # for the unknown-build/profile +50 configuration.
        for a in row['ais']:
            if configuration(a)['bonus_percent']==50:a['rating_key']='ai:SMRTBARb:bonus:50'
        lite.append(row)
    barbos.dump(fit/'matches.json',dict(matches=lite));barbos.dump(fit/'admin_reviews.json',{})
    with contextlib.redirect_stdout(io.StringIO()):barbos.rate_calibration(type('Args',(),{'output':fit})())
    fitted=json.loads((fit/'ratings.json').read_text(encoding='utf8'));by_key={r['key']:r for r in fitted['ratings']}
    configs={config_key(configuration(a)):configuration(a) for m in dataset['matches'] for a in m['ais'] if a.get('short_name','SMRTBARb').casefold()=='smrtbarb'}
    configs.setdefault(ANCHOR,ANCHOR_CONFIG)
    seeds={}
    for key,config in configs.items():
        r=by_key.get(key);is_anchor=config['bonus_percent']==50
        # Use fitted latent mean, NOT its uncertainty-penalized displayed rating.
        # This preserves estimated strength while selecting fixed seed sigma=1.
        mu=21.0 if is_anchor else r['mu'] if r else 25.0
        seeds[key]=dict(configuration=config,mu=mu,sigma=1.0,match_rating=mu-1,seed_status='owner_anchor' if is_anchor else 'provisional_training_estimate' if r else 'uncalibrated_default_prior',calibration_games=r['games'] if r else sum(any(configuration(a)['bonus_percent']==50 for a in m['ais']) for m in train) if is_anchor else 0)
    document=dict(seed_version='barbos-fixed-v1',created_at=dt.datetime.now(barbos.TZ).isoformat(),policy='All bot means and sigmas frozen; only human posteriors persist.',calibration_method='Chronological anchored joint OpenSkill fit on first 80% of eligible matches; use fitted bot mu, replace sigma with fixed 1. One-pass provisional empirical seeds, not maximum-likelihood or validated final calibration.',training_match_ids=[m['match_id'] for m in train],training_last_timestamp=train[-1]['started_at_utc'],evaluation_first_timestamp=eligible[split]['started_at_utc'] if split<len(eligible) else None,calibration_dataset_sha256=hashlib.sha256((folder/'matches.json').read_bytes()).hexdigest(),calibration_reviews_sha256=hashlib.sha256((folder/'admin_reviews.json').read_bytes()).hexdigest(),configuration_limits='AI version/profile omitted in almost all replays: explicitly unknown, not inferred from installed build. Versioned seed table cannot reconstruct historical binary versions.',seeds=seeds)
    barbos.dump(folder/'bot_seeds.json',document)
    return document

def score(rows):
    if not rows:return dict(matches=0)
    probs=[r['predicted_human_win_probability'] for r in rows];ys=[int(r['result']=='human_win') for r in rows]
    return dict(matches=len(rows),human_wins=sum(ys),observed_human_win_rate=sum(ys)/len(ys),mean_predicted_human_win_probability=sum(probs)/len(probs),brier_score=sum((p-y)**2 for p,y in zip(probs,ys))/len(rows),log_loss=-sum(y*math.log(max(p,1e-15))+(1-y)*math.log(max(1-p,1e-15)) for p,y in zip(probs,ys))/len(rows))

def run(args):
    if openskill.__version__!='5.0.1':raise ValueError('Requires openskill==5.0.1')
    folder=args.output;source=folder/'matches.json';dataset=json.loads(source.read_text(encoding='utf8'));reviews=json.loads((folder/'admin_reviews.json').read_text(encoding='utf8'))
    seed_path=folder/'bot_seeds.json'
    seeds=json.loads(seed_path.read_text(encoding='utf8')) if seed_path.exists() else build_seeds(folder,dataset,reviews)
    for key,seed in seeds['seeds'].items():
        if not math.isfinite(seed['mu']) or not math.isfinite(seed['sigma']) or seed['sigma']<=0:raise ValueError('Invalid fixed seed: '+key)
        if seed['configuration']['bonus_percent']==50 and (seed['mu'],seed['sigma'])!=(21,1):raise ValueError('+50 must remain exactly mu=21, sigma=1')
    model=PlackettLuce();humans={};records={};history=[];excluded=[];graph=collections.defaultdict(set)
    def entry(key,name,fixed=False,seed=None):
        if key not in records:records[key]=dict(key=key,names=[],games=0,wins=0,losses=0,seat_appearances=0,first_match=None,last_match=None,fixed=fixed,seed_key=key if fixed else None,seed_version=seeds['seed_version'] if fixed else None)
        if name not in records[key]['names']:records[key]['names'].append(name)
        if fixed:return model.rating(mu=seed['mu'],sigma=seed['sigma'],name=key)
        if key not in humans:humans[key]=model.rating(name=key)
        r=humans[key];return model.rating(mu=r.mu,sigma=r.sigma,name=key)
    for match in sorted(dataset['matches'],key=lambda m:(m['started_at_utc'],m['match_id'])):
        result,reasons,review=barbos.effective(match,reviews)
        ai_keys=[config_key(configuration(a)) for a in match['ais']]
        if any(k not in seeds['seeds'] for k in ai_keys):reasons.append('missing_versioned_bot_seed')
        if reasons:
            excluded.append(dict(match_id=match['match_id'],started_at_local=match['started_at_local'],map=match['map'],observed_result=match['observed_outcome']['result'],reasons=reasons,review_signals=match['review_signals'],review=review));continue
        hp=[entry(p['rating_key'],p['name']) for p in match['players']]
        bots=[entry(k,a['name'],True,seeds['seeds'][k]) for k,a in zip(ai_keys,match['ais'])]
        before={r.name:(r.mu,r.sigma) for r in hp+bots}
        keys=list(before)
        for k in keys:graph[keys[0]].add(k);graph[k].add(keys[0])
        probability=model.predict_win([hp,bots])[0];ranks=[0,1] if result=='human_win' else [1,0]
        updated_humans,_discarded_bots=model.rate([hp,bots],ranks=ranks)
        deltas=[]
        for r in updated_humans:humans[r.name]=r
        counts=collections.Counter([p['rating_key'] for p in match['players']]+ai_keys)
        for key,count in counts.items():
            fixed=key in seeds['seeds'];r=entry(key,records[key]['names'][0],True,seeds['seeds'][key]) if fixed else humans[key]
            rec=records[key];rec['games']+=1;rec['seat_appearances']+=count;win=(not fixed)==(result=='human_win');rec['wins']+=int(win);rec['losses']+=int(not win);rec['first_match']=rec['first_match'] or match['started_at_utc'];rec['last_match']=match['started_at_utc']
            if fixed:assert (r.mu,r.sigma)==(seeds['seeds'][key]['mu'],seeds['seeds'][key]['sigma'])
            deltas.append(dict(key=key,before_mu=before[key][0],before_sigma=before[key][1],after_mu=r.mu,after_sigma=r.sigma,mu_delta=r.mu-before[key][0],seat_count=count,fixed=fixed))
        history.append(dict(match_id=match['match_id'],started_at_utc=match['started_at_utc'],map=match['map'],human_count=len(hp),ai_count=len(bots),seed_keys=sorted(set(ai_keys)),seed_version=seeds['seed_version'],result=result,ranks=ranks,predicted_human_win_probability=probability,ratings=deltas,review=review))
    entry(ANCHOR,'SMRTBARb +50',True,seeds['seeds'][ANCHOR])
    anchored=set();pending=[ANCHOR]
    while pending:
        key=pending.pop()
        if key in anchored:continue
        anchored.add(key);pending.extend(graph[key]-anchored)
    ratings=[]
    for key,rec in records.items():
        seed=seeds['seeds'].get(key);r=model.rating(mu=seed['mu'],sigma=seed['sigma']) if seed else humans[key]
        ratings.append(rec|dict(mu=r.mu,sigma=r.sigma,match_rating=r.mu-r.sigma,leaderboard_rating=r.mu-3*r.sigma,connected_to_anchor=key in anchored,seed_status=seed['seed_status'] if seed else None))
    ratings.sort(key=lambda r:r['match_rating'],reverse=True)
    metadata=dict(generated_at=dt.datetime.now(barbos.TZ).isoformat(),openskill_version=openskill.__version__,model='PlackettLuce',policy='Human-only posterior persistence; all opponent seeds fixed.',parameters=dict(mu=25,sigma=25/3,beta=25/6,tau=25/300,kappa=0.0001),anchor=dict(key=ANCHOR,mu=21,sigma=1,match_rating=20,per_ai_seat=True),human_initial_prior=dict(mu=25,sigma=25/3),seed_version=seeds['seed_version'],seed_file_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),seed_configuration='AI shortname + declared version (unknown if absent) + profile (unknown if absent) + bonus',rating_scale=dict(match='mu - sigma',leaderboard='mu - 3*sigma'),matches_rated=len(history),matches_excluded=len(excluded),entities_disconnected_from_anchor=sum(not r['connected_to_anchor'] for r in ratings),human_count=len(humans),dataset_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),reviews_sha256=hashlib.sha256((folder/'admin_reviews.json').read_bytes()).hexdigest(),shared_ai_parameter_update='None: discard every bot posterior.',ai_pooling='Fixed seed per declared configuration; unknown builds/profiles cannot be resolved retrospectively.')
    barbos.dump(folder/'ratings.json',dict(metadata=metadata,ratings=ratings));barbos.dump(folder/'rating_history.json',dict(metadata=metadata,matches=history,excluded=excluded));barbos.dump(folder/'review_queue.json',excluded)
    with (folder/'ratings.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['key','names','mu','sigma','match_rating','leaderboard_rating','games','wins','losses','seat_appearances','fixed','seed_status','seed_version'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for r in ratings:w.writerow(r|{'names':' | '.join(r['names'])})
    training=set(seeds['training_match_ids']);holdout=[m for m in history if m['match_id'] not in training and m['started_at_utc']>seeds['training_last_timestamp']]
    def group(field):
        groups=collections.defaultdict(list)
        for m in holdout:
            for key in m[field] if isinstance(m[field],list) else [m[field]]:groups[str(key)].append(m)
        return {k:score(v) for k,v in groups.items()}
    evaluation=dict(seed_version=seeds['seed_version'],training_matches=len(training),holdout=score(holdout),by_map=group('map'),by_seed_configuration=group('seed_keys'),by_human_count=group('human_count'),interpretation='Forward chronological evaluation: seed calibration uses only earlier training matches; each heldout prediction occurs before that match updates human ratings. Training-period results use in-sample calibrated seeds and are not heldout evaluation.',calibration_is_provisional=True,uncalibrated_holdout_matches=sum(any(seeds['seeds'][k]['seed_status']=='uncalibrated_default_prior' for k in m['seed_keys']) for m in holdout),reviews_changed_since_calibration=seeds['calibration_reviews_sha256']!=metadata['reviews_sha256'])
    training_rows=[m for m in history if m['match_id'] in training]
    training_win_rate=sum(m['result']=='human_win' for m in training_rows)/len(training_rows) if training_rows else 0.5
    evaluation['constant_50_percent_baseline']=score([m|{'predicted_human_win_probability':0.5} for m in holdout])
    evaluation['training_win_rate_baseline']=score([m|{'predicted_human_win_probability':training_win_rate} for m in holdout])
    evaluation['calibrated_configuration_holdout']=score([m for m in holdout if all(seeds['seeds'][k]['seed_status']!='uncalibrated_default_prior' for k in m['seed_keys'])])
    evaluation['reliability_bins']={str(i):score([m for m in holdout if min(9,int(m['predicted_human_win_probability']*10))==i]) for i in range(10)}
    evaluation['ready_for_production']=False
    evaluation['reason']='Provisional seed fitting; observed heldout predictive performance must improve before rollout.'
    barbos.dump(folder/'prediction_evaluation.json',evaluation)
    print(json.dumps(dict(metadata=metadata,evaluation=evaluation['holdout']),indent=2))
