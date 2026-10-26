from pathlib import Path
import sys,random,importlib.util
root=Path('/Users/ppanati/Documents/projects/abacus/studies/23_gc_overnight_breakout_15m')
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tests'))
import phase2_verify as v
from test_phase2_independent import fixture,context,candle
from src.phase2_engine import BaselineEpisode,DecisionBar,Phase2Config,prepare_context,run_policy,PolicySpec,observe_episode,observe_levels
from src.engine import Bar
rng=random.Random(230015)
comparisons=0
for trial in range(30):
    e,m=fixture(direction=1 if trial%2==0 else -1,high=100.1 if trial%3==0 else 100.)
    e['side']='long' if e['direction']==1 else 'short'
    for i in range(1,52):
        close=round(rng.uniform(88.,103.),1)
        candle(m,i,close=close,high=round(close+rng.uniform(0,2),1),low=round(close-rng.uniform(0,2),1))
    missing=[m[30+trial]['timestamp']] if trial%5==0 else []
    c=context(e,m,missing=missing)
    ep=BaselineEpisode.from_rows(e,e)
    prod=prepare_context(ep,[Bar(x['timestamp'],x['open'],x['high'],x['low'],x['close'],x['contract']) for x in c.minutes],[DecisionBar(x['timestamp'],x['open'],x['high'],x['low'],x['close'],x['contract'],complete=x['complete']) for x in c.candles],lambda t:t in c.expected)
    for p in (*v.PRIMARY,*v.PASSIVE,*v.PROTECTED):
        kind,q,through=v.policy_details(p)
        for ordering in ('source_ohlc','high_first','low_first'):
            expected=v.oracle_policy(c,p,ordering=ordering)
            actual=run_policy(prod,PolicySpec(p,kind,q,through),Phase2Config(ordering=ordering))
            for key,value in expected.items():
                if key=='trade':
                    if value is None:v.equal(actual.get(key),None,f'{trial}:{p}:trade');continue
                    for tk,tv in value.items():
                        if tk=='stop':continue
                        v.equal(actual['trade'].get(tk),tv,f'{trial}:{p}:{ordering}:{tk}')
                        comparisons+=1
                elif key=='events':
                    comparisons+=v.compare_record({'events':actual['events']},{'events':value},f'{trial}:{p}:{ordering}:events')
                else:
                    v.equal(actual.get(key),value,f'{trial}:{p}:{ordering}:{key}')
                    comparisons+=1
    expected=v.oracle_protected(c)
    actual=observe_episode(prod)
    for table in expected:
        v.equal(len(actual[table]),len(expected[table]),f'{trial}:{table}:count')
        for index,row in enumerate(expected[table]):
            for key,value in row.items():
                v.equal(actual[table][index].get(key),value,f'{trial}:{table}:{index}:{key}');comparisons+=1
    expected=v.oracle_levels(c)
    actual=observe_levels(prod)
    for index,row in enumerate(expected):
        for key,value in row.items():
            v.equal(actual[index].get(key),value,f'{trial}:level:{index}:{key}');comparisons+=1
print({'status':'passed','synthetic_trials':30,'comparisons':comparisons})
