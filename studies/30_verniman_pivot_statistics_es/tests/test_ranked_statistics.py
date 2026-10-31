"""Denominators, population separation and independent ranked reconstruction."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from test_engine import fixture

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "src"))
sys.path.insert(0, str(STUDY))
import engine
import ranked_engine
import ranked_statistics as stats
import verify_ranked


def build(data):
    baseline = engine.analyze_day(**data)
    ranked = ranked_engine.build_ranked_day(data["session_date"],data["contract"],data["minutes"],data["bars3"],data["bars5"],pivot=data["pivot"],pivot_matched=True,vwap_rth=True)
    return ranked,baseline


class RankedStatisticsTests(unittest.TestCase):
    def test_recent_and_preceding_windows_are_disjoint_and_complete(self):
        days=[f"2020-01-{n:02d}" for n in range(1,29)]
        windows=stats.windows(days)
        for n in (20,60,120):
            recent=next(selected for kind,period,selected in windows if (kind,period)==("recent",f"last_{n}"))
            earlier=next(selected for kind,period,selected in windows if (kind,period)==("preceding",f"before_last_{n}"))
            self.assertFalse(recent & earlier)
            self.assertEqual(recent | earlier,set(days))
            self.assertEqual(len(recent),min(n,len(days)))

    def test_observed_zero_and_no_exposure_have_different_denominators(self):
        day={"session_date":"2020-01-09","contract":"ESH2020","reference":"vwap","series":"ema6","session_mode":"rth","section":"all","cohorts":["vwap_only_rth"],"crosses":0,"crosses_up":0,"crosses_down":0,"observed_hours":6.5}
        missing={**day,"session_date":"2020-01-10","observed_hours":0}
        rows=stats.summarize({"daily":[day,missing]}, {},bootstrap_replicates=0)
        cross=next(r for r in rows if r["statistic_id"]=="S01" and r["period_kind"]=="overall" and r["metric"]=="crosses" and r["direction"]=="all")
        self.assertEqual((cross["estimate"],cross["denominator"],cross["unknown"],cross["days"]),(0.,1,1,1))
        bucket=next(r for r in rows if r["statistic_id"]=="S03" and r["period_kind"]=="overall" and r["condition_value"]=="0")
        self.assertEqual((bucket["estimate"],bucket["denominator"]),(1.,1))
        verify_ranked.verify_summaries(rows,{"daily":[day,missing]}, {})

    def test_cohort_denominators_are_never_pooled(self):
        a={"session_date":"2020-01-09","reference":"vwap","series":"ema6","session_mode":"rth","section":"all","cohorts":["pivot_matched_rth","vwap_only_rth"],"crosses":1,"observed_hours":6.5}
        b={**a,"session_date":"2020-01-10","cohorts":["vwap_only_rth"],"crosses":3}
        rows=stats.summarize({"daily":[a,b]}, {},bootstrap_replicates=0)
        selected={r["cohort"]:r for r in rows if r["statistic_id"]=="S01" and r["period_kind"]=="overall" and r["metric"]=="crosses" and r["direction"]=="all"}
        self.assertEqual(selected["pivot_matched_rth"]["denominator"],1)
        self.assertEqual(selected["vwap_only_rth"]["denominator"],2)
        self.assertEqual(selected["vwap_only_rth"]["estimate"],2.)

    def test_numerical_and_independent_reconstruction_agree_on_rich_day(self):
        data=fixture(price_changes={"09:33":102.,"09:39":98.,"10:33":105.,"12:33":97.},ema_changes={"09:36":101.,"09:42":98.,"10:36":104.,"12:36":97.})
        ranked,baseline=build(data)
        checked=verify_ranked.verify_day(data["session_date"],data["contract"],data["minutes"],data["bars3"],data["bars5"],ranked,baseline)
        self.assertGreater(checked["outcome_cells"],0)
        rows=stats.summarize(ranked,baseline,bootstrap_replicates=0)
        checked=verify_ranked.verify_summaries(rows,ranked,baseline)
        self.assertGreater(checked["summary_cells"],1000)
        self.assertEqual({r["statistic_id"] for r in rows},{f"S{n:02d}" for n in range(1,21)})

    def test_independent_checker_rejects_summary_and_event_mutations(self):
        data=fixture(ema_changes={"09:33":101.,"09:39":98.})
        ranked,baseline=build(data)
        changed=deepcopy(ranked)
        changed["events"][0]["direction"] *= -1
        with self.assertRaisesRegex(ValueError,"direction"):
            verify_ranked.verify_day(data["session_date"],data["contract"],data["minutes"],data["bars3"],data["bars5"],changed,baseline)
        rows=stats.summarize(ranked,baseline,bootstrap_replicates=0)
        row=next(r for r in rows if r["statistic_id"]=="S01" and r["period_kind"]=="overall")
        row["denominator"]+=1
        with self.assertRaisesRegex(ValueError,"denominator"):
            verify_ranked.verify_summaries(rows,ranked,baseline)

    def test_block_bootstrap_resamples_complete_days(self):
        days=[f"2020-01-{n:02d}" for n in range(1,9)]
        weights=stats.block_weights(days,replicates=30,block=5,seed=20261031)
        self.assertEqual(weights.shape,(30,8))
        self.assertTrue((weights.sum(axis=1)==8).all())
        records=[{"session_date":d,"value":i,"censored":False} for i,d in enumerate(days)]
        first=stats._summarize_group(records,days=days,weights=weights)
        second=stats._summarize_group(records,days=days,weights=stats.block_weights(days,30,5,20261031))
        self.assertEqual(first,second)
        self.assertIsNotNone(first["ci95_low"])

    def test_independent_checker_reconstructs_opening_cloud_and_transitions(self):
        data=fixture(ema_changes={"09:33":101.})
        ranked,baseline=build(data)
        for table,key,value in (("daily","opening_separation_band","≥30"),("events","cloud_support","support"),("transitions","persistent",False)):
            changed=deepcopy(ranked)
            row=changed[table][0]
            row[key]=value if row[key]!=value else "changed"
            with self.assertRaises(ValueError):
                verify_ranked.verify_day(data["session_date"],data["contract"],data["minutes"],data["bars3"],data["bars5"],changed,baseline)

    def test_independent_checker_rejects_deleted_forward_and_recross_rows(self):
        data=fixture(ema_changes={"09:33":101.})
        ranked,baseline=build(data)
        for table in ("outcomes","recrosses","sequences"):
            changed=deepcopy(ranked);changed[table].pop()
            with self.assertRaisesRegex(ValueError,"roster"):
                verify_ranked.verify_day(data["session_date"],data["contract"],data["minutes"],data["bars3"],data["bars5"],changed,baseline)

    def test_rth_eligibility_survives_missing_late_globex_tail(self):
        data=fixture()
        coverage={"vwap_only_rth":True,"vwap_only_full_globex":False}
        quality={"calendar_valid":True,"rth_complete":True,"anchor_to_rth_end_complete":True,"full_globex_complete":False}
        minutes=[r for r in data["minutes"] if r["open_time"].hour!=16]
        verify_ranked.verify_cohort(data["session_date"],quality,minutes,data["bars3"],data["bars5"],coverage)
        with self.assertRaisesRegex(ValueError,"Globex cohort"):
            verify_ranked.verify_cohort(data["session_date"],quality,minutes,data["bars3"],data["bars5"],{**coverage,"vwap_only_full_globex":True})

    def test_orphan_and_duplicate_physical_events_are_rejected(self):
        data=fixture(ema_changes={"09:33":101.})
        ranked,baseline=build(data)
        changed=deepcopy(ranked)
        extra=deepcopy(changed["events"][0]);extra["scopes"]=[]
        changed["events"].append(extra)
        with self.assertRaises(ValueError):
            verify_ranked.verify_day(data["session_date"],data["contract"],data["minutes"],data["bars3"],data["bars5"],changed,baseline)

    def test_late_and_gap_windows_retain_censored_summary_candidates(self):
        for case in ("late","gap"):
            data=fixture(ema_changes={"15:45":101.,"15:48":98.} if case=="late" else {"09:33":101.,"09:39":98.})
            if case=="gap":
                next(r for r in data["minutes"] if r["close_time"].hour==9 and r["close_time"].minute==42)["vwap_valid"]=False
            baseline=engine.analyze_day(**data,require_quality=False)
            ranked=ranked_engine.build_ranked_day(data["session_date"],data["contract"],data["minutes"],data["bars3"],data["bars5"],pivot=data["pivot"],pivot_matched=True,vwap_rth=True)
            rows=stats.summarize(ranked,baseline,bootstrap_replicates=0)
            checked=verify_ranked.verify_summaries(rows,ranked,baseline)
            self.assertEqual(checked["summary_rows"],len(rows))
            delays=[r for r in rows if r["statistic_id"]=="S11" and r["metric"]=="time_to_recross" and r["period_kind"]=="overall"]
            self.assertTrue(any(r["censored"]>0 for r in delays))
            if case=="late":
                ordinal=[r for r in rows if r["statistic_id"]=="S13" and r["horizon"]=="30m" and r["period_kind"]=="overall"]
                self.assertTrue(any(r["censored"]>0 and r["unknown"]>0 for r in ordinal))


if __name__=="__main__":unittest.main()
