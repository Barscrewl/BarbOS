import unittest,tempfile,pathlib,json,gzip,struct,copy
from unittest.mock import patch
import barbos

class PipelineTests(unittest.TestCase):
    def test_tdf_names_nested_options_and_redaction(self):
        g=barbos.tdf('[GAME]{[PLAYER0]{name=[Clan]Somebody;password=secret;team=0;spectator=0;}[TEAM0]{allyteam=0;}[AI0]{shortname=SMRTBARb;team=1;[OPTIONS]{profile=Hard;}}[TEAM1]{allyteam=1;handicap=50;}mapname=Map v1;}')
        people,ais,_=barbos.roster(g)
        self.assertEqual(people[0]['name'],'[Clan]Somebody')
        self.assertEqual(people[0]['settings']['password'],'[REDACTED]')
        self.assertEqual(ais[0]['bonus_percent'],50)
        self.assertEqual(ais[0]['options']['profile'],'Hard')
    def test_stop_is_not_automatically_human_loss(self):
        m={'match_id':'x','review':dict(admin_thinks_cheated=None,exclude_from_processing=False,include_despite_automatic_flags=False,override_result=None),'automatic_flags':['stop_or_cheat_signal_requires_review','no_decisive_winner'],'observed_outcome':{'result':'unknown'}}
        self.assertTrue(barbos.effective(m,{})[1])
        outcome,reasons,_=barbos.effective(m,{'x':{'admin_thinks_cheated':True,'override_result':'ai_win'}})
        self.assertEqual((outcome,reasons),('ai_win',[]))
        outcome,reasons,_=barbos.effective(m,{'x':{'admin_thinks_cheated':True,'override_termination':'human_resign'}})
        self.assertEqual((outcome,reasons),('ai_win',[]))
        with self.assertRaises(ValueError):barbos.effective(m,{'x':{'override_result':'human_win','override_termination':'human_resign'}})
        self.assertEqual(barbos.effective(m,{'x':{'exclude_from_processing':True,'override_result':'ai_win'}})[1],['admin_excluded'])
    def test_fixed_anchor_and_sequential_human_learning(self):
        import argparse
        review=dict(admin_thinks_cheated=None,exclude_from_processing=False,include_despite_automatic_flags=False,override_result=None)
        matches=[]
        for i,outcome in enumerate(['human_win','ai_win','human_win']):
            matches.append(dict(match_id=str(i),started_at_utc=f'2026-09-16T00:0{i}:00+00:00',started_at_local='',map='fixture',players=[dict(rating_key=f'human:{n}',name=f'P{n}') for n in range(8)],ais=[dict(rating_key='ai:SMRTBARb:bonus:50',name=f'Bot{n}') for n in range(8)],review=review,automatic_flags=[],observed_outcome={'result':outcome},review_signals=[]))
            if i==1:
                for ai in matches[-1]['ais']:ai['rating_key']='ai:SMRTBARb:bonus:55'
        with tempfile.TemporaryDirectory(dir=barbos.ROOT) as temp:
            p=pathlib.Path(temp);barbos.dump(p/'matches.json',{'matches':matches});barbos.dump(p/'admin_reviews.json',{})
            barbos.rate(argparse.Namespace(output=p))
            results=json.loads((p/'ratings.json').read_text());history=json.loads((p/'rating_history.json').read_text())
            anchor=next(r for r in results['ratings'] if r['fixed'] and r['key'].endswith(':bonus:50'))
            self.assertEqual((anchor['mu'],anchor['sigma'],anchor['match_rating']),(21,1,20))
            self.assertEqual(anchor['games'],2);self.assertEqual(anchor['seat_appearances'],16)
            for match in history['matches']:
                for rating in match['ratings']:
                    if rating['fixed']:
                        self.assertEqual(rating['before_mu'],rating['after_mu'])
                        self.assertEqual(rating['before_sigma'],rating['after_sigma'])
            self.assertTrue(any(r['fixed'] and r['key'].endswith(':bonus:55') for r in results['ratings']))
            self.assertGreater(history['matches'][0]['ratings'][0]['mu_delta'],0)
            self.assertLess(history['matches'][1]['ratings'][0]['mu_delta'],0)
            self.assertEqual(history['matches'][1]['ratings'][0]['before_mu'],history['matches'][0]['ratings'][0]['after_mu'])

    def test_compressed_damage_is_retained_and_excluded(self):
        import datetime as dt
        script=('[GAME]{[TEAM0]{allyteam=0;handicap=0;}[PLAYER0]{team=0;name=Tester;spectator=0;accountid=123;}' + ''.join(f'[TEAM{i+1}]{{allyteam=1;handicap=50;}}[AI{i}]{{team={i+1};name=Bot{i};shortname=SMRTBARb;}}' for i in range(8))+'mapname=Fixture;}').encode()
        def chunk(packet):return struct.pack('<fI',0,len(packet))+packet
        stream=chunk(bytes([4])+struct.pack('<I',0))+chunk(bytes([30,4,0,1]))
        # Valid compressed body, invalid final checksum. Pad to retain readable
        # blocks when the gzip reader raises on the final block.
        raw=barbos.HEADER.pack(b'spring demofile\0',5,352,b'2026.07.04',b'x'*16,int(dt.datetime(2026,9,20,tzinfo=dt.timezone.utc).timestamp()),len(script),len(stream),1,1,1,0,20,9,0,80,15,1)+script+stream+b'\1'+b'\0'*131072
        damaged=bytearray(gzip.compress(raw));damaged[-8]^=1
        with tempfile.TemporaryDirectory(dir=barbos.ROOT) as temp:
            p=pathlib.Path(temp)/'fixture.sdfz';p.write_bytes(damaged)
            row=barbos.scan_one(p);self.assertEqual(row['status'],'selected')
            match=barbos.parse_match(row)
            self.assertEqual(len(match['ais']),8)
            self.assertIn('compression_integrity_error',match['automatic_flags'])
            self.assertIn('compression_integrity_error',barbos.effective(match,{})[1])

if __name__=='__main__':unittest.main()
