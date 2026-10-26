"""Verify the saved study bundle without rerunning source-data outcomes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


def verify(stage):
    tables=stage/'tables'
    outcomes=pd.read_csv(tables/'outcomes.csv',low_memory=False)
    metrics=pd.read_csv(tables/'metrics.csv')
    controls=pd.read_csv(tables/'matched_controls.csv')
    effects=pd.read_csv(tables/'control_effects.csv')
    races=pd.read_csv(tables/'races.csv')
    sensitivity=pd.read_csv(tables/'sensitivity_outcomes.csv')
    quality=pd.read_csv(tables/'quality_by_year.csv')
    assert set(outcomes.setup)=={'A','B','C'}
    assert set(outcomes.direction)=={-1,1}
    assert set(outcomes.horizon)=={0,5,15,30,60,120}
    assert outcomes.signal_ts.add(60_000_000_000).eq(outcomes.entry_ts).all()
    assert outcomes.minute.between(120,358).all()
    assert np.allclose(outcomes.entry*4,np.round(outcomes.entry*4))
    complete=outcomes[outcomes.path_status=='complete']
    assert (complete.mfe_points>=0).all() and (complete.mae_points>=0).all()
    assert np.allclose(complete.mfe_points*4,complete.mfe_ticks)
    assert np.allclose(complete.mae_points*20,complete.mae_dollars)
    assert (complete.holding_minutes>0).all()
    assert complete[complete.horizon==0].horizon_label.eq('to_midnight').all()
    assert complete[complete.horizon!=0].holding_minutes.eq(complete[complete.horizon!=0].horizon).all()
    primary=outcomes[(outcomes.variant=='primary')&(outcomes.horizon==30)&(outcomes.path_status=='complete')]
    assert len(primary)==len(controls)==int(metrics[(metrics.variant=='primary')&(metrics.horizon==30)].complete.sum())
    assert len(primary)==int(effects.matched.sum())
    assert controls.pool_support.gt(0).all()
    assert controls.event_signal_ts.ne(controls.control_ts).all()
    assert races.favorable_first_lower.le(races.favorable_first_upper).all()
    assert races.favorable_first_upper.le(1).all()
    assert races[['adverse_first','ambiguous','neither','target_non_hit']].ge(0).all().all()
    assert set(sensitivity.variant)=={'adjusted_snapshot','frozen_breakout_level'}
    assert sensitivity[sensitivity.variant=='frozen_breakout_level'].setup.isin(['A','B']).all()
    assert quality.year.tolist()==list(range(2010,2027))
    assert len(list((stage/'events').glob('ledger_*.jsonl.gz')))==17
    assert len(list((stage/'events').glob('sensitivity_outcomes_*.jsonl.gz')))==17
    ET.parse(stage/'figures/representative_profiles.svg')
    for name in ('report.html','report.md','advice.md','config.json','inputs.lock.json'):
        assert (stage/name).stat().st_size>0
    result={'status':'passed','primary_complete_30m':len(primary),
            'primary_horizon_records':len(outcomes),'sensitivity_horizon_records':len(sensitivity),
            'matched_controls':len(controls),'years':quality.year.tolist(),
            'figure_xml':'valid','checks':['causal next-open timestamp','entry window','price units',
             'primary denominators','control identity/support','race bounds','sensitivity separation',
             'year coverage','artifact presence']}
    (stage/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True)
    args=parser.parse_args()
    print(verify(args.stage.resolve()))
