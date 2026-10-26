"""Independent oracle fixtures and deliberate saved-ledger mutations."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import unittest
import tempfile
import csv
import json

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase3_inputs import CloudBar,CloudTimeline
from phase3_verify import (OracleDay,OracleMinute,VerificationError,compare,reference_gate,
    reference_monitoring,reference_execution,verify_gate_result,verify_monitoring,position_state,
    size_reference,economics,after_parent_fill)
from phase3_verify import bootstrap_reference,paired_reference,trade_cohorts_reference,origin
from phase3_verify import contacts_reference,contact_cohorts_reference,profile_categories,selection_reference
from phase3_verify import confluence_cohorts_reference
from phase3_verify import profiles_reference
from phase3_verify import exposure_controls_reference
from phase3_verify import risk_distance
from phase3_verify import floating_reference,history_stream_reference,GroupCursor,compare_csv,compare_stream,verify_pin,digest,bootstrap_weights

UTC=timezone.utc
T=datetime(2020,1,2,4,tzinfo=UTC)
FIVE=timedelta(minutes=5)
CONTRACT="GC:1:2020:2:GCG0"


def fixture(*,slow_touch=True,changes=None,missing=()):
    slots=[T+FIVE*i for i in range(-1,8)]
    raw=[(107,108,106,107,105,103),(100,110,99.5,108,105,103),
         (108,110,107,108,106,104),(108,110,105,108,106,104),
         (108,109,103 if slow_touch else 107.5,108,107,105),
         (108,110,108,109,107,105),(109,110,108,109,107,105),
         (109,110,108,108,107,105),(108,110,108,108,107,105)]
    clouds=[]
    for t,(o,h,l,c,a,b) in zip(slots,raw):
        row=CloudBar(t,t+FIVE,CONTRACT,o,h,l,c,a,b,2.,True,True,250)
        if changes and t in changes:row=replace(row,**changes[t])
        clouds.append(row)
    timeline=CloudTimeline(clouds,slots)
    minutes=[]
    for i in range(36):
        t=T+timedelta(minutes=i)
        cb=clouds[min(len(clouds)-1,i//5+1)]
        if t not in missing:minutes.append(OracleMinute(t,cb.open,cb.high,cb.low,cb.close,CONTRACT,t+timedelta(minutes=1)))
    parent={"trade_id":"original","broker_day":"2020-01-02","side":"long","direction":1,"contract":CONTRACT,
        "quantity":1,"status":"completed","order_submitted_at":T.isoformat(),"entry_time":T.isoformat(),
        "entry_time_latest":(T+timedelta(minutes=1)).isoformat(),"entry_time_precision":"within_bar",
        "entry_price_raw":100.,"entry_price":100.1,"initial_stop":99.,
        "reset_stop":99.1,"reset_stop_active_at":(T+timedelta(minutes=15)).isoformat(),
        "exit_time":(T+timedelta(minutes=35)).isoformat(),"exit_time_latest":(T+timedelta(minutes=35)).isoformat(),
        "exit_time_precision":"observed_open","exit_reason":"time","exit_price_raw":108.,"exit_price":107.9,
        "net_dollars":775.,"commission_dollars":5.,"gross_dollars":780.}
    return OracleDay("original","2020-01-02",parent,minutes,timeline,[T],100.,90.,T+timedelta(minutes=35),lambda t:True)


class GateAndMutationTests(unittest.TestCase):
    def saved_gate(self,day,policy):
        ep,orders=reference_gate(day,policy)
        return {"episode":ep,"orders":orders,"trades":[dict(day.parent)] if ep.get("original_filled") is True else []}

    def test_admitted_parent_is_exact_and_no_new_fill_prices(self):
        day=fixture();saved=self.saved_gate(day,"G1")
        self.assertGreater(verify_gate_result(saved,day,"G1"),20)
        saved["trades"][0]["entry_price"]+=.1
        with self.assertRaises(VerificationError):verify_gate_result(saved,day,"G1")

    def test_neutral_equality_fails_direction_gate(self):
        day=fixture(changes={T-FIVE:{"ema20":103.,"ema50":103.}})
        ep,_=reference_gate(day,"G1")
        self.assertEqual(ep["status"],"no_fill")
        self.assertEqual(ep["net_dollars"],0.)
        self.assertTrue(ep["later_opposite_entry_prohibited"])

    def test_unknown_gate_is_declared_abstention_not_unknown_execution(self):
        day=fixture(changes={T-FIVE:{"feature_valid":False,"consecutive_count":249}})
        ep,_=reference_gate(day,"G1")
        self.assertIsNone(ep["gate_admission"])
        self.assertEqual(ep["action_status"],"unknown_feature_abstention")
        self.assertEqual(ep["net_dollars"],0.)

    def test_three_change_slopes_need_four_observations(self):
        day=fixture();ep,_=reference_gate(day,"G2")
        self.assertIsNone(ep["gate_admission"])
        self.assertEqual(ep["action_status"],"unknown_feature_abstention")

    def test_later_tie_candidate_must_not_replace_standing_gate(self):
        day=fixture(changes={T:{"ema20":102.,"ema50":104.,"close":101.}})
        parent={**day.parent,"entry_time":(T+FIVE).isoformat(),"entry_time_latest":(T+FIVE+timedelta(minutes=1)).isoformat()}
        tied=replace(day,parent=parent,update_times=[T,T+FIVE])
        ep,orders=reference_gate(tied,"G1")
        self.assertEqual(orders[-1]["event"],"gate_candidate")
        self.assertEqual(ep["status"],"unknown")
        self.assertIsNone(ep["net_dollars"])
        saved=self.saved_gate(tied,"G1");saved["episode"]["status"]="no_fill";saved["episode"]["net_dollars"]=0.
        with self.assertRaises(VerificationError):verify_gate_result(saved,tied,"G1")

    def test_initial_same_opening_submission_uses_inherited_convention(self):
        day=fixture();ep,orders=reference_gate(day,"G1")
        self.assertTrue(orders[0]["coincident_shadow"])
        self.assertTrue(orders[0]["saved_initial_submission"])
        self.assertEqual(ep["status"],"completed")

    def test_unknown_and_false_cannot_be_substituted_for_counts_or_money(self):
        for actual,expected in [(False,0.),(0.,None),(False,None),(1.000000001,1)]:
            with self.subTest(actual=actual),self.assertRaises(VerificationError):compare(actual,expected)


class MonitoringTests(unittest.TestCase):
    def test_full_post_fill_and_prior_contact_level(self):
        day=fixture();rows=reference_monitoring(day)
        self.assertEqual(rows[0]["time"],(T+FIVE).isoformat().replace("+00:00","Z"))
        contact=next(r for r in rows if r["ema20_contact"])
        self.assertEqual(contact["ema20_frozen_level"],106.)
        self.assertEqual(contact["current"]["ema20"],106.)
        altered=deepcopy(rows);altered[1]["ema20_frozen_level"]=107.
        with self.assertRaises(VerificationError):verify_monitoring(altered,day)

    def test_fast_only_touch_does_not_consume_slow(self):
        rows=reference_monitoring(fixture())
        fast=next(r for r in rows if r["ema20_contact"])
        slow=next(r for r in rows if r["ema50_contact"])
        self.assertLess(fast["available_at"],slow["available_at"])
        self.assertFalse(fast["ema50_contact"])
        self.assertEqual(slow["ema50_contact_number"],1)

    def test_bounded_exit_state_unknown_and_exact_opening_exit_flat(self):
        day=fixture();end=T+timedelta(minutes=20)
        parent={**day.parent,"exit_time":end.isoformat(),"exit_time_latest":(end+timedelta(minutes=1)).isoformat(),"exit_time_precision":"within_bar"}
        self.assertEqual(position_state(parent,end),"unknown")
        self.assertEqual(position_state(parent,end+timedelta(seconds=30)),"unknown")
        self.assertEqual(position_state(parent,end+timedelta(minutes=1)),"flat")
        parent["exit_time_latest"]=parent["exit_time"]
        self.assertEqual(position_state(parent,end,before_open=True),"flat")

    def test_unknown_cloud_does_not_reuse_older_contact_level(self):
        day=fixture(changes={T+FIVE:{"usable":False,"feature_valid":False,"consecutive_count":0,"quality_reason":"missing_source_minutes"}})
        rows=reference_monitoring(day);unknown=next(r for r in rows if r["time"]==(T+2*FIVE).isoformat().replace("+00:00","Z"))
        self.assertIsNone(unknown["ema20_frozen_level"])
        self.assertFalse(unknown["prior"]["known"])

    def test_pre_entry_extremum_is_excluded_from_execution_path(self):
        day=fixture();path=after_parent_fill(day.minutes[0],day.parent,"source_ohlc")
        self.assertEqual(path[0],100.)
        self.assertNotIn(99.5,path)


class ExecutionTests(unittest.TestCase):
    def test_two_close_failure_reuses_frozen_first_edge(self):
        day=fixture(changes={T+FIVE:{"open":102.,"high":103.,"low":101.,"close":102.,"ema20":102.,"ema50":100.},
                             T+2*FIVE:{"low":101.,"close":102.}})
        result,_,signals,_,_=reference_execution(day,"X1")
        self.assertEqual(signals[0]["time"],(T+3*FIVE).isoformat().replace("+00:00","Z"))
        self.assertEqual(signals[0]["frozen_edge"],103.)
        self.assertEqual(result["signals"],1)

    def test_initial_opposition_is_not_fresh_cross_but_neutral_then_opposed_is(self):
        day=fixture(changes={T+FIVE:{"ema20":101.,"ema50":103.},T+2*FIVE:{"ema20":102.,"ema50":102.},
                             T+3*FIVE:{"ema20":101.,"ema50":103.}})
        result,_,signals,_,_=reference_execution(day,"X2")
        self.assertEqual(result["signals"],1)
        self.assertEqual(signals[0]["time"],(T+4*FIVE).isoformat().replace("+00:00","Z"))
        self.assertEqual(signals[0]["prior_alignment"],0)

    def test_monotone_trail_cannot_loosen_at_parent_reset(self):
        _,trades,_,actions,_=reference_execution(fixture(),"T50")
        original=next(t for t in trades if t["leg"]=="original")
        self.assertEqual(original["reset_stop"],99.1)
        self.assertGreater(original["effective_stop"],original["reset_stop"])
        trail=[e["effective_stop"] for e in actions if e["event"]=="trail_future_activation"]
        self.assertEqual(trail,sorted(trail))

    def test_already_breached_trail_exits_next_open_not_at_proposed_stop(self):
        _,trades,signals,_,_=reference_execution(fixture(changes={T:{"ema20":112.,"ema50":110.05}}),"T50")
        original=next(t for t in trades if t["leg"]=="original")
        self.assertEqual(signals[0]["proposed_stop"],109.9)
        self.assertEqual(original["exit_time"],(T+2*FIVE).isoformat().replace("+00:00","Z"))
        self.assertEqual(original["exit_price_raw"],108.)

    def test_two_add_policies_have_separate_first_signal(self):
        day=fixture();a=reference_execution(day,"A20");b=reference_execution(day,"A50")
        self.assertEqual(a[0]["signals"],1)
        self.assertEqual(b[0]["signals"],1)
        self.assertLess(a[2][0]["time"],b[2][0]["time"])
        self.assertEqual(a[0]["add_attempts"],1)
        self.assertEqual(b[0]["add_attempts"],1)

    def test_rejected_first_contact_never_selects_later_better_contact(self):
        day=fixture(changes={T+2*FIVE:{"close":105.,"ema20":104.,"ema50":106.}})
        result,trades,orders,_,_=reference_execution(day,"A20")
        self.assertEqual(result["add_attempts"],1)
        self.assertEqual(result["signals"],0)
        self.assertFalse(any(t["leg"]=="add" for t in trades))

    def test_known_close_signal_survives_missing_next_opening(self):
        day=fixture(missing=[T+3*FIVE]);result,trades,orders,_,_=reference_execution(day,"A20")
        self.assertEqual(result["signals"],1)
        self.assertEqual(len(orders),1)
        self.assertEqual(result["add_fills"],0)
        self.assertEqual(result["status"],"censored")
        self.assertIsNone(result["net_dollars"])

    def test_missing_contact_close_cannot_confirm(self):
        day=fixture(changes={T+2*FIVE:{"usable":False,"feature_valid":False,"consecutive_count":0,"quality_reason":"missing_source_minutes"}},missing=[T+timedelta(minutes=14)])
        result,_,orders,_,_=reference_execution(day,"A20")
        self.assertEqual(result["signals"],0)
        self.assertEqual(orders,[])

    def test_opening_parent_stop_cancels_contingent_add(self):
        day=fixture();minutes=[replace(b,open=98.,high=98.,low=97.,close=98.) if b.timestamp==T+3*FIVE else b for b in day.minutes]
        result,_,_,_,_=reference_execution(replace(day,minutes=minutes),"A20")
        self.assertEqual(result["signals"],1)
        self.assertEqual(result["add_fills"],0)
        self.assertEqual(result["pending_add_cancellations"],1)

    def test_add_five_minute_reset_and_parent_fifteen_minute_reset(self):
        result,trades,_,_,_=reference_execution(fixture(slow_touch=False),"A20")
        original=next(t for t in trades if t["leg"]=="original")
        add=next(t for t in trades if t["leg"]=="add")
        self.assertEqual(original["reset_stop_active_at"],(T+3*FIVE).isoformat().replace("+00:00","Z"))
        self.assertEqual(add["reset_stop_active_at"],(T+4*FIVE).isoformat().replace("+00:00","Z"))
        self.assertEqual(add["reset_stop"],107.)
        self.assertEqual(result["original_fills"],1)

    def test_unknown_initial_contact_prefix_abstains_irrevocably(self):
        day=fixture(changes={T:{"feature_valid":False,"consecutive_count":249}})
        result,_,orders,_,_=reference_execution(day,"A20")
        self.assertIsNone(result["add_opportunity"])
        self.assertEqual(result["add_attempts"],1)
        self.assertEqual(orders,[])

    def test_original_quantity_skip_is_not_a_financed_landmark(self):
        day=fixture();result,trades,orders,_,_=reference_execution(day,"A20",mode="financed_overlay",equity_start=10.)
        self.assertEqual(result["status"],"no_fill")
        self.assertEqual(result["net_dollars"],0.)
        self.assertEqual(trades,[])
        self.assertEqual(orders,[])

    def test_reserved_raw_risk_and_whole_quantity_no_cost_replenishment(self):
        cfg=economics();result=size_reference(10000,.5,100.,99.,1,cfg)
        self.assertEqual(result["budget_dollars"],50.)
        self.assertEqual(result["planned_risk_per_contract"],100.)
        self.assertEqual(result["quantity"],0)
        more=size_reference(10000,.5,100.,99.9,1,cfg)
        self.assertEqual(more["quantity"],5)

    def test_mtm_and_trade_price_mutations_are_detected(self):
        result,trades,_,_,exposure=reference_execution(fixture(),"A20")
        mutated=deepcopy(trades);mutated[0]["net_dollars"]+=10
        with self.assertRaises(VerificationError):compare(mutated,trades,"trades")
        mutated=deepcopy(exposure);mutated[2]["max_mtm_drawdown"]+=1
        with self.assertRaises(VerificationError):compare(mutated,exposure,"exposure")


class AggregateMutationTests(unittest.TestCase):
    def test_confluence_categories_use_saved_actual_field_names(self):
        state={"known":True,"direction":1,"ema20_high_confluence":True,"ema50_high_confluence":False,
               "duration_left_censored":True}
        result=profile_categories(state,1)
        self.assertEqual(result["confluence_ema20_H"],"yes")
        self.assertEqual(result["confluence_ema50_H"],"no")
        self.assertEqual(result["confluence_ema20_M"],"unknown")
        self.assertEqual(result["aligned_duration"],"left_censored")

    def test_contact_breach_requires_full_tick_beyond_raw_ema(self):
        day=fixture();rows=reference_monitoring(day)
        contact=next(r for r in rows if r["ema20_contact"])
        contact["ema20_frozen_level"]=106.05;contact["low"]=106.
        records,_=contacts_reference(rows,{day.episode_id:day.parent})
        event=next(r for r in records if r["ema"]==20)
        self.assertEqual(event["breach_level"],105.9)
        self.assertFalse(event["tick_breach"])

    def test_known_reclaim_survives_gap_but_exact_first_timing_does_not(self):
        day=fixture();rows=reference_monitoring(day)
        rows[2]["usable"]=False
        records,_=contacts_reference(rows,{day.episode_id:day.parent})
        event=next(r for r in records if r["ema"]==20)
        self.assertTrue(event["reclaimed"])
        self.assertIsNone(event["reclaim_at"])
        self.assertIsNone(event["recovery_minutes"])
        self.assertFalse(event["recovery_time_known"])
        self.assertEqual(event["recovery_delay_lower"],0.)
        self.assertEqual(event["recovery_delay_upper"],10.)
        summary=contact_cohorts_reference(records,rows)
        total=next(r for r in summary if r["ema"]==20 and r["contact_group"]=="all" and r["event"]=="reclaimed"
                   and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(total["known_events"],1)
        self.assertEqual(total["recovery_timing_denominator"],0)
        self.assertEqual(total["observed_recovery_timing_unknown"],1)

    def test_forward_paths_exclude_event_candle_and_cutoff_overrun(self):
        day=fixture();rows=reference_monitoring(day)
        _,forward=contacts_reference(rows,{day.episode_id:day.parent})
        first=next(r for r in forward if r["ema"]==20 and r["horizon_minutes"]==5)
        self.assertEqual(first["mfe_points"],1.)
        self.assertEqual(first["mae_points"],5.)
        long=next(r for r in forward if r["ema"]==20 and r["horizon_minutes"]==60)
        self.assertEqual(long["status"],"censored")
        self.assertIsNone(long["mfe_points"])

    def test_unknown_account_capital_is_not_quantity_zero(self):
        result,trades,orders,_,_=reference_execution(fixture(),"A20",mode="financed_overlay",equity_start=None)
        self.assertEqual(result["status"],"unknown")
        self.assertIsNone(result["original_quantity"])
        self.assertIsNone(result["net_dollars"])
        self.assertEqual(trades,[])
        self.assertEqual(orders,[])

    def test_selection_requires_adjusted_positive_support_and_financed_adds(self):
        parents={};trades=[]
        for i in range(100):
            eid=str(i);year=2021 if i<50 else 2022
            parents[eid]={"entry_time":f"{year}-06-01T12:00:00Z","direction":1}
            for p in ("G1","G2","A20","A50","X1","X2"):
                trades.append({"episode_id":eid,"policy":p,"mode":"financed_overlay" if p.startswith("A") else "standardized",
                               "status":"completed","leg":"original"})
        paired=[{"policy":p,"year":"validation","session":"all","side":"combined","mean_difference":10.,
                 "adjusted_low":1.,"complete_pairs":100} for p in ("G1","G2","A20","A50","X1","X2")]
        selection=selection_reference(paired,[],trades,parents)
        self.assertEqual(selection["selected_gate"],"G1")
        self.assertEqual(selection["selected_exit"],"X1")
        self.assertEqual(selection["selected_adds"],[])
        self.assertIsNone(selection["combined_policy"])
        paired[0]["adjusted_low"]=0.
        self.assertEqual(selection_reference(paired,[],trades,parents)["selected_gate"],"G2")

    def test_block_intervals_keep_known_zero_and_null_distinct(self):
        result=bootstrap_reference([("2020-01-01",[0.,None]),("2020-02-01",[0.,None])],
            ["2020-01-01","2020-02-01","2020-03-01"],replications=1000)
        self.assertTrue(all(v==0 for v in result[0].values()))
        self.assertTrue(all(v is None for v in result[1].values()))

    def test_block_extremes_and_same_draw_confidence_levels(self):
        result=bootstrap_reference([("2020-01-01",[1.]),("2020-02-01",[3.])],
            ["2020-01-01","2020-02-01"],replications=10000)
        self.assertEqual(result,[{"difference_low":1.,"difference_high":3.,"adjusted_low":1.,"adjusted_high":3.}])

    def test_six_policy_common_mask_retains_individual_unknowns(self):
        parents={"a":{**fixture().parent,"broker_day":"2020-01-02"},"b":{**fixture().parent,"broker_day":"2020-02-03"}}
        episodes=[]
        for eid in parents:
            for mode in ["parent_1","half_parent"]:
                episodes.append({"episode_id":eid,"policy":"BASE","mode":mode,"status":"completed","net_dollars":1.,"original_fills":1})
            for policy in ["G1","G2","A20","A50","X1","X2"]:
                row={"episode_id":eid,"policy":policy,"mode":"financed_overlay" if policy.startswith("A") else "standardized",
                     "status":"completed","net_dollars":2.,"original_fills":1}
                if eid=="b" and policy=="G1":row.update(status="censored",net_dollars=None)
                episodes.append(row)
        rows,effects,common=paired_reference(episodes,parents,["2020-01-02","2020-02-03"],intervals=False)
        top=[r for r in rows if r["year"]=="all" and r["session"]=="all" and r["side"]=="combined"]
        self.assertEqual(common,{"a":True,"b":False})
        self.assertEqual(top[0]["complete_pairs"],1)
        self.assertEqual(top[0]["missing_pairs"],1)
        self.assertEqual(top[1]["individual_pairs"],2)
        mutated=deepcopy(top);mutated[1]["complete_pairs"]=2
        with self.assertRaises(VerificationError):compare(mutated,top,"paired")

    def test_within_year_drawdown_restarts_and_actual_leg_year_anchor(self):
        trades=[]
        for eid,entry,exit_,net in [("a","2019-12-30T15:00:00Z","2019-12-30T16:00:00Z",-100.),
                                  ("b","2020-01-02T15:00:00Z","2020-01-02T16:00:00Z",-5.),
                                  ("c","2020-01-03T15:00:00Z","2020-01-03T16:00:00Z",100.)]:
            trades.append({"trade_id":eid,"episode_id":eid,"policy":"X1","mode":"standardized","leg":"original",
                "entry_time":entry,"exit_time":exit_,"direction":1,"quantity":1,"status":"completed","net_dollars":net})
        rows,_,_=trade_cohorts_reference(trades,[{"policy":"X1","mode":"standardized"}])
        top=next(r for r in rows if r["year"]=="all" and r["session"]=="all" and r["side"]=="combined" and r["leg"]=="combined")
        annual=next(r for r in rows if r["year"]=="2020" and r["session"]=="all" and r["side"]=="combined" and r["leg"]=="combined")
        self.assertEqual(top["closed_drawdown_dollars"],105.)
        self.assertEqual(annual["closed_drawdown_dollars"],5.)
        self.assertEqual(origin("2022-01-01T04:30:00Z",1)["year"],"2021")
        self.assertEqual(origin("2022-01-01T06:00:00Z",1)["year"],"2022")

    def test_reporting_outside_gap_and_new_york_start(self):
        self.assertEqual(origin("2020-07-02T13:15:00Z",1)["session"],"Outside")
        self.assertEqual(origin("2020-07-02T13:30:00Z",1)["session"],"New York")


class RetainedEvidenceMutationTests(unittest.TestCase):
    def row(self,eid,at,net=5.):
        return dict(policy="X1",mode="standardized",episode_id=eid,time=at,closed_net_dollars=net,
            active_quantity=0,mtm_net_dollars=net,intraminute_mtm_min=-10.,intraminute_mtm_max=20.,
            max_mtm_drawdown=30.,notional=1000.,combined_active_stop_risk=20.,concurrent_legs=1)

    def test_unknown_without_exposure_blocks_later_floating_history(self):
        parents={str(i):dict(entry_time=f"2020-01-0{i}T04:00:00Z",direction=1) for i in (2,3,4)}
        episodes=[dict(policy="X1",mode="standardized",episode_id=eid,status="unknown" if eid=="3" else "completed",net_dollars=None if eid=="3" else 5.) for eid in parents]
        exposure=[self.row("2","2020-01-02T04:00:00Z"),self.row("4","2020-01-04T04:00:00Z")]
        history=list(history_stream_reference(iter(exposure),parents,episodes))
        self.assertEqual([r["episode_id"] for r in history],["2"])
        table=floating_reference(iter(exposure),parents,episodes)
        top=next(r for r in table if r["year"]==r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(top["observed_mtm_rows"],1)
        self.assertIsNone(top["mtm_drawdown_dollars"])
        self.assertEqual(top["observed_prefix_mtm_drawdown_dollars"],30.)
        self.assertEqual(top["unknown_episode_equity"],1)

    def test_first_censored_episode_retains_its_observed_marks(self):
        parents={str(i):dict(entry_time=f"2020-01-0{i}T04:00:00Z",direction=1) for i in (2,3)}
        episodes=[dict(policy="X1",mode="standardized",episode_id=eid,status="censored" if eid=="2" else "completed",net_dollars=None if eid=="2" else 5.) for eid in parents]
        exposure=[self.row("2","2020-01-02T04:00:00Z"),self.row("2","2020-01-02T04:01:00Z"),self.row("3","2020-01-03T04:00:00Z")]
        self.assertEqual(len(list(history_stream_reference(iter(exposure),parents,episodes))),2)
        top=next(r for r in floating_reference(iter(exposure),parents,episodes) if r["year"]==r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(top["observed_mtm_rows"],2)
        self.assertFalse(top["full_path_known"])

    def test_zero_financed_abstention_has_known_zero_floating(self):
        parents={"x":dict(entry_time="2020-01-02T04:00:00Z",direction=1)}
        episodes=[dict(policy="A20",mode="financed_overlay",episode_id="x",status="no_fill",net_dollars=0.)]
        top=next(r for r in floating_reference(iter(()),parents,episodes) if r["year"]==r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(top["mtm_drawdown_dollars"],0.)
        self.assertTrue(top["full_path_known"])
        self.assertEqual(top["peak_notional"],0.)

    def test_stream_group_cannot_hide_out_of_order_extra_episode(self):
        cursor=GroupCursor(iter([dict(eid="a"),dict(eid="b"),dict(eid="a")]),lambda r:r["eid"])
        self.assertEqual(len(cursor.take("a")),1)
        self.assertEqual(len(cursor.take("b")),1)
        with self.assertRaises(VerificationError):cursor.exhausted()

    def test_csv_mutations_in_value_null_bool_and_roster_fail(self):
        expected=[dict(count=1,money=0.,unknown=None,flag=False,name="x")]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"saved.csv"
            def save(row):
                with path.open("w",newline="") as f:
                    writer=csv.DictWriter(f,fieldnames=list(expected[0]));writer.writeheader();writer.writerow(row)
            save(expected[0]);self.assertEqual(compare_csv(path,expected),(5,1))
            for key,value in [("count","1.5"),("money","False"),("unknown",0),("flag","")]:
                save(dict(expected[0],**{key:value}))
                with self.subTest(key=key),self.assertRaises(VerificationError):compare_csv(path,expected)
            save(expected[0])
            with self.assertRaises(VerificationError):compare_csv(path,[])

    def test_exact_byte_pin_rejects_file_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source";path.write_text("frozen")
            record=dict(path="source",sha256=digest(path),bytes=6)
            self.assertEqual(verify_pin(tmp,record),path)
            path.write_text("retuned")
            with self.assertRaises(VerificationError):verify_pin(tmp,record)

    def test_stream_length_mismatch_and_changed_source_cell_fail(self):
        self.assertEqual(compare_stream(iter([dict(x=2.)]),iter([dict(x=2.)]),"rows"),(1,1))
        with self.assertRaises(VerificationError):compare_stream(iter([dict(x=3.)]),iter([dict(x=2.)]),"rows")
        with self.assertRaises(VerificationError):compare_stream(iter([]),iter([dict(x=2.)]),"rows")

    def test_resampling_multiplicity_preserves_every_block_draw(self):
        import numpy as np
        weights=bootstrap_weights(5,500,230015)
        rng=np.random.default_rng(230015)
        direct=np.concatenate([rng.integers(0,5,size=(250,5)),rng.integers(0,5,size=(250,5))])
        for i in (0,249,250,499):self.assertTrue(np.array_equal(weights[i],np.bincount(direct[i],minlength=5)))
        self.assertTrue(np.all(weights.sum(axis=1)==5))


class ContactCloudContextTests(unittest.TestCase):
    def contacts(self,*,unknown=False):
        change={"ema20":103.,"ema50":106.}
        if unknown:change.update(feature_valid=False,consecutive_count=249)
        day=replace(fixture(changes={T+2*FIVE:change}),high=106.)
        monitor=reference_monitoring(day)
        return contacts_reference(monitor,{"original":day.parent})[0],monitor

    def test_cloud_flip_at_contact_uses_prior_and_current_known_order(self):
        records,monitor=self.contacts()
        first=next(r for r in records if r["ema"]==20)
        self.assertTrue(first["cloud_flip"])
        self.assertTrue(first["confluence_H"])
        self.assertFalse(first["confluence_L"])
        self.assertFalse(first["confluence_M"])
        changed=[dict(r) for r in records];changed[records.index(first)]["cloud_flip"]=False
        with self.assertRaises(VerificationError):compare(changed,records)

    def test_unknown_current_cloud_retains_unknown_flip_not_false(self):
        records,monitor=self.contacts(unknown=True)
        first=next(r for r in records if r["ema"]==20)
        self.assertIsNone(first["cloud_flip"])
        self.assertTrue(first["confluence_H"])
        top=next(r for r in contact_cohorts_reference(records,monitor) if r["ema"]==20 and r["contact_group"]=="first" and r["event"]=="cloud_flip" and r["year"]==r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(top["unknown"],1)
        self.assertIsNone(top["rate"])
        self.assertEqual((top["lower_bound"],top["upper_bound"]),(0.,1.))

    def test_confluence_rows_partition_flags_and_recovery_breach_risk(self):
        base=dict(episode_id="x",ema=20,year="2020",session="Asia",side="long",confluence_H=True,confluence_L=False,confluence_M=None,
            hold=True,tick_breach=False,close_break=False,reclaimed=None,cloud_flip=True)
        records=[base,dict(base,episode_id="y",tick_breach=True,reclaimed=True,cloud_flip=None)]
        rows=confluence_cohorts_reference(records)
        self.assertEqual(len(rows),13500)
        def pick(level,state,event):return next(r for r in rows if r["ema"]==20 and r["level"]==level and r["confluence_state"]==state and r["event"]==event and r["year"]==r["session"]=="all" and r["side"]=="combined")
        recovery=pick("H","yes","reclaimed")
        self.assertEqual((recovery["contacts"],recovery["known_events"],recovery["known_denominator"]),(1,1,1))
        flip=pick("H","yes","cloud_flip")
        self.assertEqual((flip["known_events"],flip["unknown"],flip["contacts"]),(1,1,2))
        self.assertEqual((flip["rate"],flip["lower_bound"],flip["upper_bound"]),(1.,.5,1.))
        self.assertEqual(pick("M","unknown","hold")["contacts"],2)
        self.assertEqual(pick("L","no","hold")["contacts"],2)
        mutated=dict(recovery,contacts=2)
        with self.assertRaises(VerificationError):compare(mutated,recovery)

    def test_empty_profile_buckets_are_explicit_zero_support(self):
        parents={"x":dict(direction=1,status="completed",net_dollars=5.,broker_day="2020-01-02")}
        observations=[dict(episode_id="x",anchor="original_entry",decision_at="2020-01-02T04:00:00Z",snapshot=dict(known=False))]
        rows=profiles_reference(observations,parents,["2020-01-02"],intervals=False)
        neutral=next(r for r in rows if r["anchor"]=="original_entry" and r["feature"]=="ordering" and r["bucket"]=="neutral" and r["year"]==r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(neutral["observations"],0)
        self.assertEqual(neutral["distinct_episodes"],0)
        self.assertIsNone(neutral["mean_parent_net_dollars"])
        self.assertIsNone(neutral["mean_low"])
        self.assertFalse(any(r["anchor"]=="eligible_open_position_landmark" for r in rows))
        unknown=next(r for r in rows if r["feature"]=="availability" and r["bucket"]=="unknown" and r["year"]==r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(unknown["observations"],1)
        self.assertEqual(unknown["mean_parent_net_dollars"],5.)
        with self.assertRaises(VerificationError):compare(dict(neutral,mean_parent_net_dollars=0.),neutral)

    def test_extra_exposure_controls_share_all_three_known_masks(self):
        parents={"x":dict(entry_time="2020-01-02T04:00:00Z",direction=1),"y":dict(entry_time="2020-01-03T04:00:00Z",direction=1)}
        episodes=[]
        for eid in parents:
            for p,m,v in (("BASE","parent_1",10.),("BASE","parent_2",None if eid=="y" else 20.),("A20","diagnostic_1plus1",15.),("A50","diagnostic_1plus1",5.)):
                episodes.append(dict(episode_id=eid,policy=p,mode=m,status="completed" if v is not None else "censored",net_dollars=v))
        rows=exposure_controls_reference(episodes,parents)
        self.assertEqual(len(rows),600)
        overall=[r for r in rows if r["policy"]=="A20" and r["year"]==r["session"]=="all" and r["side"]=="combined"]
        self.assertEqual([r["complete_pairs"] for r in overall],[1,1])
        self.assertEqual([r["individual_pairs"] for r in overall],[2,1])
        self.assertEqual([r["total_difference"] for r in overall],[5.,-5.])
        self.assertTrue(all(r["larger_exposure"] and r["not_equal_risk"] for r in overall))
        with self.assertRaises(VerificationError):compare(dict(overall[0],complete_pairs=2),overall[0])

    def test_management_holding_bounds_use_actual_fill_and_exit_intervals(self):
        day=fixture();ep,trades,*_=reference_execution(day,"A20",mode="diagnostic_1plus1")
        original=next(r for r in trades if r["leg"]=="original")
        add=next(r for r in trades if r["leg"]=="add")
        self.assertEqual((original["holding_minutes_lower"],original["holding_minutes_upper"]),(34.,35.))
        # This fixture's add stops inside its entry minute, so its interval
        # includes a possible zero-duration fill/exit and one minute upper.
        self.assertEqual((add["holding_minutes_lower"],add["holding_minutes_upper"]),(0.,1.))
        with self.assertRaises(VerificationError):compare(dict(original,holding_minutes_lower=35.),original)

    def test_original_profile_parent_path_is_not_misassigned_to_later_events(self):
        parents={"x":dict(direction=1,status="completed",net_dollars=5.,broker_day="2020-01-02",mfe_points=2.,mae_points=1.,holding_minutes=45.)}
        observations=[dict(episode_id="x",anchor=a,decision_at="2020-01-02T04:00:00Z",snapshot=dict(known=False)) for a in ("original_entry","eligible_open_position_landmark")]
        rows=profiles_reference(observations,parents,["2020-01-02"],intervals=False)
        selected=[r for r in rows if r["feature"]=="availability" and r["bucket"]=="unknown" and r["year"]==r["session"]=="all" and r["side"]=="combined"]
        entry=next(r for r in selected if r["anchor"]=="original_entry")
        later=next(r for r in selected if r["anchor"]=="eligible_open_position_landmark")
        self.assertEqual((entry["mean_parent_mfe_points"],entry["mean_parent_mae_points"],entry["mean_parent_holding_minutes"]),(2.,1.,45.))
        self.assertTrue(all(later[k] is None for k in ("mean_parent_mfe_points","mean_parent_mae_points","mean_parent_holding_minutes")))
        with self.assertRaises(VerificationError):compare(dict(later,mean_parent_mfe_points=2.),later)

    def test_risk_metadata_near_tick_identity_does_not_quantize_real_off_tick(self):
        raw=102.10000000000001
        self.assertEqual(risk_distance(raw,102.1,1,.1),0.)
        self.assertEqual(risk_distance(102.15,102.1,1,.1),.05)
        self.assertEqual(raw,102.10000000000001)
        self.assertEqual(risk_distance(102.1,103.2,-1,.1),1.1)


if __name__=="__main__":unittest.main()
