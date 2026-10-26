#!/usr/bin/env python3
"""Fixed local-only examples from saved ledgers; no resimulation or publication."""
import argparse
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from src.spec import PRODUCTS
from src.events import select_events
from src.statistics import baseline_policy_mask
from src.storage import save_csv,save_json,sha
from src.core import FIVE

def main():
    p=argparse.ArgumentParser();p.add_argument("--work",type=Path,required=True);w=p.parse_args().work
    examples=[];candles=[]
    for product in PRODUCTS:
        ev=pd.read_parquet(w/"private"/f"events_{product}.parquet")
        paths=pd.read_parquet(w/"private"/f"outcomes_{product}.parquet")
        trades=pd.read_parquet(w/"private"/f"trades_{product}.parquet")
        bars=pd.read_parquet(w/"private"/f"bars_{product}.parquet")
        eligible=select_events(ev,"3","none").sort_values(["confirmation_ts","event_id"])
        aligned=select_events(ev,"3","alignment").sort_values(["confirmation_ts","event_id"])
        fifteen=paths[paths.horizon==15]
        losing=set(fifteen[fifteen.completed&(fifteen.delta<0)].event_id)
        missing=set(fifteen[fifteen.entered&~fifteen.completed].event_id)
        ambiguous=set(trades[baseline_policy_mask(trades,"alignment","stop_first")&trades.ambiguous.fillna(False)].event_id)
        selectors={"accepted_long":aligned[aligned.direction==1],"accepted_short":aligned[aligned.direction==-1],"cloud_rejected":eligible[eligible.alignment==False],"losing_15bar":aligned[aligned.event_id.isin(losing)],"missing_15bar":eligible[eligible.event_id.isin(missing)],"barrier_ambiguous":aligned[aligned.event_id.isin(ambiguous)]}
        for category,g in selectors.items():
            if not len(g):
                examples.append({"product":product,"category":category,"status":"no matching event","selection":"chronologically first matching event over all frozen splits"})
                continue
            e=g.iloc[0];out=fifteen[fifteen.event_id==e.event_id]
            examples.append({"product":product,"category":category,"status":"selected","selection":"chronologically first matching event over all frozen splits, ties event_id","event_id":e.event_id,"day":e.day,"split":e.split,"direction":e.direction,"alignment":e.alignment,"pivot":e.pivot,"atr":e.atr,"delta_15bar":out.iloc[0].delta if len(out) else np.nan,"completed":out.iloc[0].completed if len(out) else False})
            block=bars[(bars.ts>=e.confirmation_ts-3*FIVE)&(bars.ts<e.entry_ts+15*FIVE)&(bars.day==e.day)].copy()
            block["example_product"]=product;block["example_category"]=category;block["example_event_id"]=e.event_id;block["example_pivot"]=e.pivot;block["example_confirmation_ts"]=e.confirmation_ts
            candles.append(block)
    save_csv(w/"tables/examples.csv",pd.DataFrame(examples))
    pd.concat(candles,ignore_index=True).to_parquet(w/"private/examples_bars.parquet",index=False)
    save_json(w/"example-selection.json",{"rule":"chronologically first eligible matching category in all frozen splits; includes negative/missing/ambiguous cases; no attractive-winner selection","source":"saved event, outcome, trade and bar ledgers; no calculation rerun","public":False,"output_sha256":sha(w/"tables/examples.csv")})

if __name__=="__main__":main()
