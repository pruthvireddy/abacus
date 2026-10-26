"""Next-open OHLC excursion and first-passage measurements.

All functions are pure: no disk reads, no eligibility lookahead masquerading
as a feature, and no assumed ordering of a candle's high and low.
"""
from __future__ import annotations
import math
import numpy as np


def excursion(open_,high,low,close,direction,volatility=math.nan,width=math.nan):
    if direction not in (-1,1) or not len(open_):raise ValueError('valid side and nonempty path required')
    entry=float(open_[0])
    favorable=np.asarray(high)-entry if direction==1 else entry-np.asarray(low)
    adverse=entry-np.asarray(low) if direction==1 else np.asarray(high)-entry
    mfe=max(0.,float(favorable.max()));mae=max(0.,float(adverse.max()))
    terminal=direction*(float(close[-1])-entry)
    result={'entry':entry,'mae_points':mae,'mfe_points':mfe,'terminal_points':terminal,
            'mae_ticks':mae*4,'mfe_ticks':mfe*4,'terminal_ticks':terminal*4,
            'mae_dollars':mae*20,'mfe_dollars':mfe*20,'terminal_dollars':terminal*20,
            'first_mfe_bar':int(np.argmax(favorable)) if mfe>0 else None,
            'first_mae_bar':int(np.argmax(adverse)) if mae>0 else None}
    for label,denominator in [('tr60',volatility),('va_width',width)]:
        for key,value in [('mae',mae),('mfe',mfe),('terminal',terminal)]:
            result[f'{key}_{label}']=value/denominator if math.isfinite(denominator) and denominator>0 else None
    return result


def race(open_,high,low,direction,favorable_distance,adverse_distance):
    """Unconditional target/stop bounds; opening gaps resolve known order.

    A bar index is an interval [index,index+1) after entry, not a fabricated
    exact intraminute time. Pre-target MAE is reported with ordering bounds.
    """
    if favorable_distance<=0 or adverse_distance<=0 or not math.isfinite(favorable_distance+adverse_distance):
        return None
    entry=float(open_[0]);open_=np.asarray(open_)
    favorable=np.asarray(high)-entry if direction==1 else entry-np.asarray(low)
    adverse=entry-np.asarray(low) if direction==1 else np.asarray(high)-entry
    opened=direction*(open_-entry)
    f=np.flatnonzero(favorable>=favorable_distance);a=np.flatnonzero(adverse>=adverse_distance)
    fi=int(f[0]) if len(f) else None;ai=int(a[0]) if len(a) else None
    if fi is None and ai is None:status='neither'
    elif ai is None or (fi is not None and fi<ai):status='favorable_first'
    elif fi is None or ai<fi:status='adverse_first'
    elif opened[fi]>=favorable_distance:status='favorable_first_open_gap'
    elif opened[fi]<=-adverse_distance:status='adverse_first_open_gap'
    else:status='same_bar_ambiguous'
    favorable_first=status.startswith('favorable_first')
    ambiguous=status=='same_bar_ambiguous'
    # On target's hit candle adverse movement can precede or follow the hit.
    before=max(0.,float(adverse[:fi].max())) if fi is not None and fi>0 else 0.
    lower=max(before,max(0.,-float(opened[fi]))) if fi is not None else None
    upper=max(before,max(0.,float(adverse[fi]))) if fi is not None else None
    if fi is not None and opened[fi]>=favorable_distance:upper=lower=before
    return {'status':status,'favorable_hit_bar':fi,'adverse_hit_bar':ai,
            'favorable_hit_at_open':bool(fi is not None and opened[fi]>=favorable_distance),
            'adverse_hit_at_open':bool(ai is not None and opened[ai]<=-adverse_distance),
            'favorable_first_lower':int(favorable_first),'favorable_first_upper':int(favorable_first or ambiguous),
            'target_hit':fi is not None,'non_hit':fi is None,
            'pre_target_mae_lower':lower,'pre_target_mae_upper':upper}


def structural(open_,high,low,direction,reference):
    if reference is None or not math.isfinite(reference):
        return {'defined':False,'ahead':None,'range_hit':None,'directional_reach':None}
    entry=float(open_[0]);distance=direction*(reference-entry)
    reached=np.asarray(high)>=reference if direction==1 else np.asarray(low)<=reference
    intersect=(np.asarray(low)<=reference)&(np.asarray(high)>=reference)
    return {'defined':True,'ahead':bool(distance>0),'range_hit':bool(intersect.any()),
            'directional_reach':bool(reached.any()),'distance_points':float(distance)}


def fixed_path(timestamps,entry_index,minute_of_entry,horizon,minute_ns=60_000_000_000):
    """Elapsed minutes, entry candle included, horizon closes by midnight."""
    if minute_of_entry+horizon>360:return None,'midnight_censored'
    end=entry_index+horizon
    if end>len(timestamps):return None,'missing_future_minutes'
    expected=timestamps[entry_index]+np.arange(horizon)*minute_ns
    if not np.array_equal(timestamps[entry_index:end],expected):return None,'missing_future_minutes'
    return slice(entry_index,end),'complete'
