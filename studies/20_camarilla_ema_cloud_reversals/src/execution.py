import itertools
import json
from fractions import Fraction
import numpy as np
import pandas as pd
from .events import build_events, select_events, label_paths
from .replay import policy, minute_arrays
from .spec import PRODUCTS, MODES
from .storage import save_json, utc_now
from .core import exact_price

EXTENSIONS = ("slope", "wick", "rvol", "approach_half_atr", "tolerance", "cooldown", "strict", "warm500", "rollbuffer")

def configurations():
    configs = []
    for pair, mode, target, order in itertools.product(("2","3","4"), MODES, ("3R","2R","pivot"), ("stop_first","target_first")):
        configs.append(dict(pair=pair,mode=mode,target=target,order=order))
    for mode, fee, slip, order in itertools.product(("none","alignment"),(5,10,15),(0,1,2),("stop_first","target_first")):
        if fee != 10 or slip != 1:
            configs.append(dict(pair="3",mode=mode,fee=fee,slip=slip,order=order))
    for mode, order in itertools.product(("none","alignment"),("stop_first","target_first")):
        configs.extend([dict(pair="3",mode=mode,delay=1,order=order),dict(pair="3",mode=mode,touch=True,order=order),dict(pair="3",mode=mode,window_name="session",order=order)])
    for ext, order in itertools.product(EXTENSIONS,("stop_first","target_first")):
        configs.append(dict(pair="3",mode="alignment",extension=ext,order=order))
    for pair, mode, order in itertools.product(("control225","control325"),("none","alignment"),("stop_first","target_first")):
        configs.append(dict(pair=pair,mode=mode,order=order))
    for order in ("stop_first","target_first"):
        configs.append(dict(pair="4",mode="alignment",extension="continuation",order=order))
    return configs

def execute(work):
    if (work/"scoring-complete.json").exists():
        raise RuntimeError("Scoring already completed; never retune or overwrite")
    save_json(work/"scoring-started.json", {"started_at":utc_now(),"protocol_frozen_before_outcomes":True,"no_parameter_selection":True})
    tall, sall = [], []
    for product in PRODUCTS:
        bars=pd.read_parquet(work/"private"/f"bars_{product}.parquet")
        minutes=pd.read_parquet(work/"private"/f"minutes_{product}.parquet")
        coverage=pd.read_csv(work/"tables"/f"coverage_{product}.csv",dtype={"day":str,"prior_day":str,"contract":str})
        events=build_events(product,bars,coverage)
        for coefficient,label in ((1.1/6,"2"),(1.1/4,"3"),(1.1/2,"4")):
            support=events.prior_close-coefficient*events.prior_range
            resistance=events.prior_close+coefficient*events.prior_range
            cf=Fraction(str(coefficient)).limit_denominator(1000000)
            events["touch_S"+label]=events.apply(lambda r:exact_price(r.confirmation_low)<=exact_price(r.prior_close)-cf*exact_price(r.prior_range),axis=1)
            events["touch_R"+label]=events.apply(lambda r:exact_price(r.confirmation_high)>=exact_price(r.prior_close)+cf*exact_price(r.prior_range),axis=1)
        opens=bars[bars.minute_NY==570].set_index("day").open
        events["NY_open_position_R3_ATR"]=(events.day.map(opens)-events.prior_close-.275*events.prior_range)/events.atr
        events.loc[events.entry_minute_NY<570,"NY_open_position_R3_ATR"]=np.nan
        bar_lookup=bars.set_index("ts")
        events["fast_slope5_ATR"]=events.confirmation_ts.map(bar_lookup.fast_slope)/events.atr
        events["slow_slope5_ATR"]=events.confirmation_ts.map(bar_lookup.slow_slope)/events.atr
        starts=bars.groupby("contract").day.min().to_dict()
        events["rollbuffer_ok"]=events.apply(lambda e: np.busday_count(starts[e.contract],e.day)>=2,axis=1)
        prior_ranges=(coverage.high-coverage.low).where(coverage.HLC_valid).shift().rolling(20,min_periods=20).median()
        range_medians=dict(zip(coverage.day,prior_ranges))
        events["range_relative20"]=events.prior_range / events.day.map(range_medians)
        dev=events[(events.split=="development") & events.seed_valid & events.first_episode & events.main_eligible & (events.variant=="core") & (events.pair=="3") & (events.entry_minute_NY>=570) & (events.entry_minute_NY<690)]
        boundaries={key:dev[key].quantile([1/3,2/3]).tolist() for key in ("prior_range","atr")}
        for key,cuts in boundaries.items():
            events[key+"_tertile"]=pd.cut(events[key],[-np.inf,*cuts,np.inf],labels=("low","middle","high")).astype("string") if len(set(cuts))==2 else pd.NA
        save_json(work/f"development-context-{product}.json",{"learned_from":"development technical R3/S3 first events; no strategy outcomes", "tertile_boundaries":boundaries})
        events.to_parquet(work/"private"/f"events_{product}.parquet",index=False)
        candidates=events[events.seed_valid & (events.first_episode.fillna(False)|events.cooldown.fillna(False))]
        paths,orders=label_paths(candidates,bars,minutes)
        paths.to_parquet(work/"private"/f"outcomes_{product}.parquet",index=False)
        orders.to_parquet(work/"private"/f"ordering_{product}.parquet",index=False)
        print(f"{product}: common opportunity and independent-path ledgers saved",flush=True)
        ma=minute_arrays(minutes)
        trade_parts,session_parts=[],[]
        cache={}
        configs=configurations()
        for k,c in enumerate(configs):
            ext=c.get("extension","core")
            win=c.get("window_name","main")
            eligible_col="session_eligible" if win=="session" else ("strict_eligible" if ext=="strict" else ("warm500_eligible" if ext=="warm500" else "eligible"))
            roster=coverage[coverage[eligible_col]].copy()
            if ext=="rollbuffer":
                roster=roster[roster.apply(lambda r:np.busday_count(starts[r.contract],r.day)>=2,axis=1)]
            ev=select_events(events,c["pair"],c["mode"],ext,win,product)
            # Subset gates apply to the policy roster as well as event features.
            ev=ev[ev.day.isin(roster.day)]
            t,s=policy(ev,roster,ma,product,cache=cache,**c)
            trade_parts.append(t);session_parts.append(s)
            if (k+1)%25==0:
                print(f"{product}: {k+1}/{len(configs)} fixed policy configurations replayed",flush=True)
        pd.concat(trade_parts,ignore_index=True).to_parquet(work/"private"/f"trades_{product}.parquet",index=False)
        pd.concat(session_parts,ignore_index=True).to_parquet(work/"private"/f"policy_sessions_{product}.parquet",index=False)
        print(f"{product}: all declared simulations saved",flush=True)
    save_json(work/"scoring-complete.json",{"completed_at":utc_now(),"policy_configurations_per_product":len(configurations()),"evaluation":"all frozen splits, no retuning", "optional_unavailable":["daily21","settlement parity","VWAP gate","100-bar overnight"]})
