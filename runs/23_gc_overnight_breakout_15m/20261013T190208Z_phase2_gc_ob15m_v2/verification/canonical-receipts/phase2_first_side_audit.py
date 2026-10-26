"""Read-only pinned original-minute first-side ambiguity audit."""
from pathlib import Path
import argparse,gzip,hashlib,json
import pyarrow.parquet as pq


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',type=Path,required=True);a=p.parse_args()
    stage=a.stage.resolve();root=Path(__file__).resolve().parents[2]
    if not stage.is_relative_to(root/'work/23_gc_overnight_breakout_15m'):raise ValueError('new owning stage')
    pin=json.loads((stage/'phase2-baseline-pin.json').read_text());records=[]
    def ledger(name):
        r=next(x for x in pin['scenario_ledgers'] if x['id']==name)
        path=root/r['locator']
        if sha(path)!=r['sha256']:raise ValueError('changed original ledger')
        records.append(r)
        with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]
    originals=ledger('primary-one-tick-trades');ranges={r['broker_day']:r for r in ledger('primary-one-tick-days')}
    minute_pin=pin['prepared_execution_inputs']['audit-minutes'];path=root/minute_pin['locator']
    if sha(path)!=minute_pin['sha256']:raise ValueError('changed pinned minutes')
    frame=pq.read_table(path,columns=['timestamp','open','high','low','close','contract']).to_pandas().set_index('timestamp')
    import pandas as pd
    dual=[];unknown=[];ambiguous=[]
    for t in originals:
        m=frame.loc[pd.Timestamp(t['entry_time'])];r=ranges[t['broker_day']];h,l=r['range_high'],r['range_low']
        if m['contract']!=t['contract']:raise ValueError('original contract mismatch')
        record=dict(episode_id=t['trade_id'],broker_day=t['broker_day'],entry_time=t['entry_time'],direction=t['direction'],precision=t['entry_time_precision'],open=float(m.open),high=float(m.high),low=float(m.low),close=float(m.close),range_high=h,range_low=l,baseline_ambiguous=t.get('ambiguous',False),inside_open=l<float(m.open)<h)
        if t.get('ambiguous'):ambiguous.append(record)
        if m.high>=h and m.low<=l:
            dual.append(record)
            if record['inside_open']:unknown.append(record)
    result=dict(status='passed',scope='pinned Phase1 original fill minutes only; no alternative policy outcomes recalculated',original_episodes=len(originals),both_range_boundaries_visited_in_fill_minute=len(dual),inside_open_unresolved_first_side=len(unknown),baseline_ambiguous_flags=len(ambiguous),dual_minutes=dual,unresolved_first_side_minutes=unknown,interpretation='Complete b does not resolve intraminute first-side order. Zero observed unresolved dual-side originals means this retained-history issue has zero support; synthetic uncertainty remains a separate requirement.',input_pins=[*records,minute_pin],checker_sha256=sha(Path(__file__)))
    output=stage/'verification/original-first-side-audit.json';output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','original_episodes','both_range_boundaries_visited_in_fill_minute','inside_open_unresolved_first_side','baseline_ambiguous_flags')},indent=2))


if __name__=='__main__':main()
