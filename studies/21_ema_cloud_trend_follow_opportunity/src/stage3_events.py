"""Independent chronological absolute/ATR gateway acceptance, without outcomes.

Absolute streams freshly execute the inherited selected-boundary engine. ATR
streams own the same causal arm/consume rules, with a dimensionless width gate.
There is no period/fold scoring mask, cooldown or future-path filter here.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .engine import _ordered, _strata, generate_events
from .stage2_engine import _fast_stream


def gate_spec(family: str, threshold: float) -> dict:
    threshold = float(threshold)
    if family not in ('absolute', 'atr') or not math.isfinite(threshold) or threshold < 0 or (family == 'atr' and threshold == 0):
        raise ValueError('gate family/finite threshold unsupported; zero belongs to absolute only')
    token = format(threshold, '.12g').replace('.', 'p')
    return dict(gate_id=('abs_' if family == 'absolute' else 'atr_')+token, family=family, threshold=threshold)


def _atr_stream(mapped_bars, interval_minutes, touch_mode, threshold):
    bars = _ordered(mapped_bars)
    bars['interval_minutes'] = interval_minutes
    n = len(bars)
    fields={'direction':np.zeros(n,dtype=np.int8),'width':np.full(n,np.nan),
        'min_width':np.full(n,np.nan),'episode_id':np.zeros(n,dtype=np.int64),'signal_idx':np.zeros(n,dtype=np.int64)}
    for column in ('width_pass','slow_touch','fast_touch','penetration','full_departure',
                   'armed_before','armed_after','technical_candidate','setup_candidate','accepted'):
        fields[column]=np.zeros(n,dtype=bool)
    reasons,resets=np.full(n,'no_touch',object),np.full(n,'',object)
    epsilon=1e-10*max(1.,abs(threshold))
    for product,group in bars.groupby('product',sort=False):
        armed,previous_direction,previous_contract,episode=False,0,None,0
        previous_source_reset=None
        for ordinal,row in enumerate(group.itertuples()):
            i=row.Index
            fields['signal_idx'][i]=ordinal
            atr_valid=bool(np.isfinite(row.atr14) and row.atr14>0)
            fields['min_width'][i]=threshold*row.atr14 if atr_valid else np.nan
            valid=bool(row.usable) and bool(row.feature_valid) and np.isfinite(row.ema20) and np.isfinite(row.ema50)
            direction=(1 if row.ema20>row.ema50 else -1 if row.ema20<row.ema50 else 0) if valid else 0
            fields['direction'][i]=direction
            reset_source=getattr(row,'feature_source_timestamp',row.timestamp)
            explicit_reset=bool(row.feature_reset) and reset_source!=previous_source_reset
            reset='invalid_data_or_feature' if not valid else 'equality' if direction==0 else 'contract_change' if previous_contract is not None and row.contract!=previous_contract else 'feature_reset' if explicit_reset else 'direction_change' if direction!=previous_direction else ''
            if reset:
                armed=False;resets[i]=reset
            fields['armed_before'][i]=armed
            if valid and direction:
                width=abs(row.ema20-row.ema50)
                fast_touch=row.low<=row.ema20<=row.high
                slow_touch=row.low<=row.ema50<=row.high
                selected=row.ema20 if touch_mode=='fast' else row.ema50
                touch=fast_touch if touch_mode=='fast' else slow_touch
                penetration=row.low<=selected if direction==1 else row.high>=selected
                departure=row.low>max(row.ema20,row.ema50) if direction==1 else row.high<min(row.ema20,row.ema50)
                passed=bool(atr_valid and width/row.atr14+epsilon>=threshold)
                candidate=bool(touch and armed)
                accepted=bool(candidate and passed)
                fields['width'][i]=width
                for column,value in (('width_pass',passed),('slow_touch',slow_touch),('fast_touch',fast_touch),
                    ('penetration',penetration),('full_departure',departure),('technical_candidate',touch),
                    ('setup_candidate',candidate),('accepted',accepted)):
                    fields[column][i]=value
                other=slow_touch if touch_mode=='fast' else fast_touch
                reasons[i]='accepted' if accepted else 'not_armed' if touch and not armed else 'atr_invalid' if candidate and not atr_valid else 'width_below_minimum' if candidate and not passed else 'gap_penetration' if penetration and not touch else ('slow_only' if touch_mode=='fast' else 'fast_only') if other and not touch else 'no_touch'
                # Consumption does not depend on successful width/ATR gating.
                if penetration:armed=False
                if departure:
                    if not armed:episode+=1
                    armed=True
            else:
                reasons[i]='invalid_data_or_feature' if not valid else 'no_direction'
            fields['armed_after'][i]=armed;fields['episode_id'][i]=episode
            previous_direction,previous_contract=direction,row.contract
            if bool(row.feature_reset):previous_source_reset=reset_source
    for key,values in fields.items():bars[key]=values
    bars['suppression_reason'],bars['reset_reason']=reasons,resets
    bars['side']=np.select([bars.direction.eq(1),bars.direction.eq(-1)],['Buy','Sell'],default='None')
    bars['event_id']=None
    accepted=bars.accepted
    if accepted.any():
        bars.loc[accepted,'event_id']=(bars.loc[accepted,'product'].astype(str)+'|'+str(interval_minutes)+'m|'+
            bars.loc[accepted,'contract'].astype(str)+'|'+bars.loc[accepted,'timestamp'].map(lambda t:t.isoformat())+
            '|'+bars.loc[accepted,'side']+'|'+touch_mode)
    events=bars.loc[accepted].copy()
    events['signal_timestamp']=events.timestamp
    events['reference_price']=events.close
    events['entry_at']=events.available_at
    events['entry_atr']=events.atr14.where(np.isfinite(events.atr14)&events.atr14.gt(0))
    events=_strata(events)
    return bars,events.reset_index(drop=True)


def generate_gateway_stream(mapped_bars: pd.DataFrame, interval_minutes: int,
                            touch_mode: str, gate: dict) -> dict:
    if type(interval_minutes) is not int or interval_minutes not in (3,5) or touch_mode not in ('fast','slow'):
        raise ValueError('unsupported signal interval/touch mode')
    if mapped_bars.empty or mapped_bars['product'].nunique()!=1:
        raise ValueError('gateway stream requires one nonempty product roster')
    spec=gate_spec(gate['family'],gate['threshold'])
    if gate.get('gate_id')!=spec['gate_id']:
        raise ValueError('noncanonical gateway identity')
    product=str(mapped_bars['product'].iloc[0])
    if product not in ('ES','GC','NQ'):
        raise ValueError('unsupported gateway product')
    if spec['family']=='absolute':
        function=_fast_stream if touch_mode=='fast' else generate_events
        technical,events=function(mapped_bars,interval_minutes,{product:spec['threshold']})
    else:
        technical,events=_atr_stream(mapped_bars,interval_minutes,touch_mode,spec['threshold'])
    for frame in (technical,events):
        frame['touch_mode']=touch_mode
        frame['selected_ema']='ema20' if touch_mode=='fast' else 'ema50'
        frame['gate_id']=spec['gate_id']
        frame['gate_family']=spec['family']
        frame['gate_threshold']=spec['threshold']
        frame['width_ratio']=frame.width/ frame.atr14.where(np.isfinite(frame.atr14)&frame.atr14.gt(0))
    events['stage']=3
    events['split']='causal_unscored'
    return dict(bars=mapped_bars,technical=technical,events=events,product=product,
                interval_minutes=interval_minutes,touch_mode=touch_mode,gate=spec)


def iter_gateway_streams(mapped_bars: pd.DataFrame, interval_minutes: int,
                         gates, touch_modes=('fast','slow')):
    """Yield only caller-declared gates, one complete branch ledger at a time."""
    gates=list(gates)
    modes=tuple(touch_modes)
    if len({g['gate_id'] for g in gates})!=len(gates) or len(set(modes))!=len(modes):
        raise ValueError('duplicate gateway/branch request')
    for gate in gates:
        for mode in modes:
            yield generate_gateway_stream(mapped_bars,interval_minutes,mode,gate)


def generate_gateway_streams(mapped_bars, interval_minutes, gates, touch_modes=('fast','slow')):
    """Small-fixture convenience; production should consume the iterator."""
    payloads=list(iter_gateway_streams(mapped_bars,interval_minutes,gates,touch_modes))
    if not payloads:
        return pd.DataFrame(),pd.DataFrame()
    technical=pd.concat([p['technical'] for p in payloads],ignore_index=True)
    events=pd.concat([p['events'] for p in payloads],ignore_index=True)
    return technical,events
