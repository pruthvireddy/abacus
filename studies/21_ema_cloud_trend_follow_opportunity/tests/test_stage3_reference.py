import copy
from pathlib import Path
import json
import unittest

import numpy as np
import pandas as pd

from src import stage3_reference as ref
from src.stage3_events import generate_gateway_stream
from src.stage3_masks import ScoringPeriod, event_masks
from src.stage3_outcomes import score_period


def config():
    return json.loads((Path(__file__).resolve().parents[1]/"config-stage3.json").read_text())


def roster(n=16, start="2019-01-02T14:00Z", interval=5):
    stamps=pd.date_range(start,periods=n,freq=f"{interval}min")
    lows=np.resize([103.,102.,100.,103.,101.,99.,103.,102.],n)
    frame=pd.DataFrame(dict(product="ES",interval_minutes=interval,contract="ESH9",timestamp=stamps,
        available_at=stamps+pd.Timedelta(minutes=interval),open=lows+1,high=lows+2,low=lows,close=lows+1,
        usable=True,feature_valid=True,feature_reset=False,ema20=102.,ema50=100.,atr14=4.,
        session="2019-01-02",quality_reason="complete",known_closure_before=False))
    return frame


class Authorization:
    start="2018-01-01";end="2021-01-01"
    def validate(self,*args):pass


class ReferenceTests(unittest.TestCase):
    def test_independent_absolute_atr_streams_all_fields(self):
        bars=roster(40)
        bars.loc[4,"atr14"]=0.
        bars.loc[10,"feature_valid"]=False
        bars.loc[13,["ema20","ema50"]]=100.
        bars.loc[20:,["ema20","ema50"]]=[98.,100.]
        bars.loc[20:,["low","high","close"]]=[97.,101.,99.]
        bars.loc[24,["low","high","close"]]=[95.,97.,96.]
        bars.loc[27,"contract"]="ESM9"
        bars.loc[30,"feature_reset"]=True
        gates=[dict(gate_id=ref.gate_id(f,t),family=f,threshold=t) for f,t in (("absolute",0.),("absolute",2.),("absolute",3.),("atr",.5),("atr",1.))]
        tech,events=ref.reference_stream(bars,gates)
        for gate in gates:
            for branch in ("fast","slow"):
                got=generate_gateway_stream(bars,5,branch,gate)
                expected=tech.loc[tech.gate_id.eq(gate["gate_id"]) & tech.touch_mode.eq(branch)].reset_index(drop=True)
                from src.stage3_reconcile import compare_frames,STATE_FIELDS,IDENTITY_FIELDS
                compare_frames(got["technical"],expected,["signal_idx"],STATE_FIELDS)
                e=events.loc[events.gate_id.eq(gate["gate_id"]) & events.touch_mode.eq(branch)]
                compare_frames(got["events"],e,["event_id"],IDENTITY_FIELDS)

    def test_masks_invalid_slots_count_closures_absent_and_exact_endpoint(self):
        bars=roster(130,start="2019-01-01T05:00Z")
        bars.loc[:99,"usable"]=False
        # A known closure changes elapsed clock time without adding slots.
        bars.loc[105:,["timestamp","available_at"]]+=pd.Timedelta(hours=2)
        cfg=config();cfg["development_folds"]=[dict(id="2019H1",start="2019-01-01",end=bars.available_at.iloc[120].isoformat())]
        cfg["periods"]["final"]=dict(start="2019-01-01",end=bars.available_at.iloc[120].isoformat())
        masks=ref.reference_masks(bars,cfg,"final",[1,15],signal_indices=[99,100,105,120]).set_index(["signal_idx","horizon"])
        self.assertTrue(masks.loc[(99,1),"start_embargo"])
        self.assertFalse(masks.loc[(100,1),"start_embargo"])
        self.assertFalse(masks.loc[(105,15),"endpoint_purge"])
        self.assertTrue(masks.loc[(120,1),"endpoint_purge"])
        gate=dict(gate_id="abs_0",family="absolute",threshold=0.)
        _,events=ref.reference_stream(bars,[gate],("fast",))
        period=ScoringPeriod("final","final",cfg["periods"]["final"]["start"],cfg["periods"]["final"]["end"])
        actual,_=event_masks(bars,events,[1,15],period)
        expected=ref.reference_masks(bars,cfg,"final",[1,15],events.signal_idx.unique())
        from src.stage3_reconcile import compare_frames
        compare_frames(actual,expected,["signal_idx","horizon"],["start_embargo","endpoint_purge","score_eligible","mask_reason","terminal_signal_idx"])

    def test_scalar_forward_paths_null_quality_and_sell_attainment(self):
        bars=roster(160)
        gate=dict(gate_id="abs_0",family="absolute",threshold=0.)
        _,events=ref.reference_stream(bars,[gate],("slow",))
        events=events.loc[events.signal_idx.between(100,140)].copy()
        bars.loc[112,"known_closure_before"]=True
        bars.loc[123,["usable","contract"]]=[False,None]
        bars.loc[123,"quality_reason"]="missing"
        cfg=config();cfg["canonical_start_embargo_slots"]=0
        period=ScoringPeriod("development","2019H1","2019-01-01","2019-07-01",0)
        actual,_=score_period(bars,events,[1,3,15],period,Authorization(),product="ES",interval_minutes=5,touch_mode="slow",gate=gate)
        expected=ref.reference_outcomes(bars,events,cfg,"development",[1,3,15])
        from src.stage3_reconcile import compare_frames,IDENTITY_FIELDS,PATH_FIELDS
        compare_frames(actual,expected,["event_id","horizon"],IDENTITY_FIELDS+PATH_FIELDS)
        self.assertTrue(actual.censor_reason.eq("invalid_future_slot:missing").any())
        self.assertTrue(actual.loc[actual.status.eq("censored"),"favorable"].isna().all())

    def test_period_week_rosters_and_identity_undefined_bootstrap(self):
        from datetime import timedelta
        for p in config()["periods"].values():
            first=ref.boundary(p["start"]).tz_convert(ref.NY).date();first-=timedelta(days=first.weekday())
            last=(ref.boundary(p["end"])-pd.Timedelta(nanoseconds=1)).tz_convert(ref.NY).date()
            expected=[]
            while first<=last:expected.append(first.isoformat());first+=timedelta(weeks=1)
            self.assertEqual(ref.week_roster(p["start"],p["end"]),expected)
        f=pd.DataFrame(dict(status=["completed"],terminal_delta_atr=[1.],session=["2024-01-02"],week=["2024-01-01"]))
        r=ref.reference_uncertainty(f,f,"terminal_delta_atr",ref.week_roster("2024-01-01","2026-01-01"),draws=40)
        self.assertEqual(r["estimate"],0.);self.assertEqual(r["ci_low"],0.)
        empty=f.iloc[:0];r=ref.reference_uncertainty(empty,empty,"terminal_delta_atr",["2024-01-01"],draws=20)
        self.assertIsNone(r["estimate"]);self.assertIsNone(r["adjusted_low"]);self.assertEqual(r["undefined_draws"],20)

    def test_undefined_guards_fail_without_zero_substitution(self):
        columns=["fold_id","horizon","atr_support","status","session","week","terminal_delta_atr","mfe_atr","mae_atr"]
        empty=pd.DataFrame(columns=columns)
        got=ref.candidate_assessment(empty,empty,config())
        self.assertFalse(got["eligible"]);self.assertFalse(got["guards"]["defined"])
        self.assertIsNone(got["score"]);self.assertIsNone(got["retention"])


if __name__=="__main__":unittest.main()
