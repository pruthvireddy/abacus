"""Meaningful invariants for roster, risk controls and chronological metrics."""
import unittest

from phase3_metrics import (anchor,session_at,closed_path,block_intervals,
    paired_rows,profile_values,profile_rows,contact_diagnostics,confluence_rows,exposure_control_rows,selection,risk_rows,stream_exposure_paths,exposure_cohorts,CORE,policy_mode)


class Phase3MetricTests(unittest.TestCase):
    def test_dst_cross_midnight_actual_calendar_year(self):
        self.assertEqual(session_at("2021-01-01T05:30:00Z"),"Asia")
        self.assertEqual(anchor("2021-01-01T05:30:00Z",1)["year"],"2021")
        self.assertEqual(session_at("2021-07-01T13:15:00Z"),"Outside")
        self.assertEqual(session_at("2021-07-01T13:30:00Z"),"New York")
        self.assertEqual(session_at("2021-01-01T14:30:00Z"),"New York")

    def test_within_year_drawdown_does_not_import_prior_peak(self):
        trades=[dict(status="completed",trade_id=str(i),exit_time=f"202{i}-06-01T17:00:00Z",net_dollars=v) for i,v in ((0,100),(1,-20),(2,10),(3,-15))]
        path,dd=closed_path(trades)
        self.assertEqual(dd,25)
        within,dd=closed_path(trades[2:])
        self.assertEqual(dd,15)
        self.assertEqual(within[0]["cumulative_net_dollars"],10)

    def roster(self):
        parents={"win":dict(entry_time="2021-01-04T08:00:00Z",direction=1,broker_day="2021-01-04",net_dollars=100,status="completed"),
                 "loss":dict(entry_time="2021-01-05T08:00:00Z",direction=1,broker_day="2021-01-05",net_dollars=-80,status="completed"),
                 "unknown":dict(entry_time="2021-01-06T08:00:00Z",direction=1,broker_day="2021-01-06",net_dollars=None,status="censored")}
        rows=[]
        for i,t in parents.items():
            for p,m,v in [("BASE","parent_1",t["net_dollars"]),("BASE","half_parent",0),*[(p,policy_mode(p),0 if p in {"A20","A50","G1"} else t["net_dollars"]) for p in CORE]]:
                rows.append(dict(episode_id=i,broker_day=t["broker_day"],policy=p,mode=m,net_dollars=v,status="no_fill" if v==0 else "completed" if v is not None else "censored",original_fills=0 if v==0 else 1,signals=0))
        return rows,parents,[t["broker_day"] for t in parents.values()]

    def test_no_fill_zero_unknown_null_common_and_individual_masks(self):
        rows,parents,days=self.roster()
        saved,effects,common=paired_rows(rows,parents,days,intervals=False,cohorts=[("all","all","combined")])
        g1=next(r for r in saved if r["policy"]=="G1")
        self.assertEqual(g1["complete_pairs"],2)
        self.assertEqual(g1["missing_pairs"],1)
        self.assertEqual(g1["mean_difference"],-10)
        self.assertEqual(g1["missed_winners"],1)
        self.assertEqual(g1["avoided_losses"],1)
        add=next(r for r in saved if r["policy"]=="A20")
        self.assertEqual(add["individual_pairs"],3)
        self.assertEqual(add["mean_difference"],0)
        self.assertFalse(common["unknown"])

    def test_block_empty_spacing_and_reproducibility(self):
        dates=["2021-01-04","2021-04-05"]
        values=[("2021-01-04",[0,None]),("2021-04-05",[20,40])]
        a=block_intervals(values,dates,reps=1000)
        self.assertEqual(a,block_intervals(values,dates,reps=1000))
        self.assertEqual(a[1]["difference_low"],40)
        self.assertLessEqual(a[0]["adjusted_low"],a[0]["difference_low"])
        self.assertGreaterEqual(a[0]["adjusted_high"],a[0]["difference_high"])

    def test_confluence_equality_and_duration_unknown_prefix(self):
        state=profile_values(dict(known=True,direction=0,price_cloud="inside",slope20_3=0,slope50_3=0,ema20_high_confluence=True,ema50_low_confluence=False,duration_left_censored=True,aligned_count=50),1)
        self.assertEqual(state["ordering"],"neutral")
        self.assertEqual(state["confluence_ema20_H"],"yes")
        self.assertEqual(state["confluence_ema50_L"],"no")
        self.assertEqual(state["confluence_ema20_M"],"unknown")
        self.assertEqual(state["aligned_duration"],"left_censored")

    def test_never_observed_neutral_and_fixed_bins_have_zero_support_not_zero_profit(self):
        parents={"e":dict(direction=1,broker_day="2021-01-04",entry_time="2021-01-04T08:00:00Z",status="completed",net_dollars=10)}
        observed=[dict(episode_id="e",anchor="original_entry",decision_at=parents["e"]["entry_time"],snapshot=dict(known=True,direction=1,price_cloud="above",width_atr=.1,favorable_distance_atr=.1))]
        rows=profile_rows(observed,parents,["2021-01-04"],intervals=False)
        neutral=next(r for r in rows if r["anchor"]=="original_entry" and r["feature"]=="ordering" and r["bucket"]=="neutral" and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertEqual((neutral["observations"],neutral["distinct_episodes"],neutral["completed_parent_episodes"]),(0,0,0))
        self.assertIsNone(neutral["mean_parent_net_dollars"])
        self.assertIsNone(neutral["parent_win_rate"])
        self.assertTrue(any(r["feature"]=="width_atr" and r["bucket"]==">=2" and r["observations"]==0 for r in rows))

    def test_parent_path_context_is_entry_only_and_never_claims_post_event_excursions(self):
        parents={"e":dict(direction=1,broker_day="2021-01-04",entry_time="2021-01-04T08:00:00Z",status="completed",net_dollars=10,mfe_points=5,mae_points=3,holding_minutes=60)}
        observed=[dict(episode_id="e",anchor=a,decision_at=parents["e"]["entry_time"],snapshot=dict(known=True,direction=1,price_cloud="above",width_atr=.1,favorable_distance_atr=.1)) for a in ("original_entry","eligible_open_position_landmark")]
        rows=profile_rows(observed,parents,["2021-01-04"],intervals=False)
        select=lambda a:next(r for r in rows if r["anchor"]==a and r["feature"]=="distance_atr" and r["bucket"]=="[0,0.5)" and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        entry=select("original_entry");event=select("eligible_open_position_landmark")
        self.assertEqual((entry["mean_parent_mfe_points"],entry["mean_parent_mae_points"],entry["mean_parent_holding_minutes"]),(5,3,60))
        self.assertIsNone(event["mean_parent_mfe_points"])
        self.assertIsNone(event["mean_parent_mae_points"])

    def test_contact_tick_and_separate_reclaim_forward_excludes_source(self):
        parent={"e":dict(direction=1,broker_day="2021-01-04")}
        def bar(t,close,low,contact=False):
            return dict(episode_id="e",time=f"2021-01-04T{t}:00Z",available_at=f"2021-01-04T{t[:3]}{int(t[3:])+5:02}:00Z",close=close,high=close+1,low=low,contract="GC",usable=True,open_position_landmark=True,parent_liquidation_net_unit=1,ema20_contact=contact,ema50_contact=False,ema20_frozen_level=100.05,ema20_contact_number=1)
        bars=[bar("08:00",100.1,99.9,True),bar("08:05",100.2,100.1),bar("08:10",100.3,100.2)]
        contacts,forward=contact_diagnostics(bars,parent)
        self.assertTrue(contacts[0]["tick_breach"])
        self.assertEqual(contacts[0]["reclaim_at"],"2021-01-04T08:10:00Z")
        five=next(r for r in forward if r["horizon_minutes"]==5)
        self.assertAlmostEqual(five["signed_points"],.1)
        self.assertEqual(next(r for r in forward if r["horizon_minutes"]==15)["status"],"censored")

    def test_no_selection_on_positive_unfunded_add_or_sparse_fills(self):
        rows,parents,days=self.roster()
        candidates=[dict(policy=p,year="validation",session="all",side="combined",mean_difference=100,adjusted_low=1,complete_pairs=2) for p in CORE]
        result=selection(candidates,rows,[],parents)
        self.assertIsNone(result["selected_gate"])
        self.assertIsNone(result["selected_exit"])
        self.assertEqual(result["selected_adds"],[])

    def test_contact_cloud_flip_and_frozen_confluence_keep_unknowns_and_event_denominators(self):
        parent={"e":dict(direction=-1,broker_day="2021-01-04")}
        row=dict(episode_id="e",time="2021-01-04T08:00:00Z",available_at="2021-01-04T08:05:00Z",close=100,high=100.2,low=99,contract="GC",usable=True,open_position_landmark=True,parent_liquidation_net_unit=1,ema20_contact=True,ema50_contact=False,ema20_frozen_level=100.05,ema20_contact_number=2,prior=dict(known=True,alignment=0,ema20_high_confluence=True,ema20_low_confluence=False,ema20_midpoint_confluence=None),current=dict(known=True,alignment=-1))
        records,_=contact_diagnostics([row],parent)
        self.assertTrue(records[0]["cloud_flip"])
        self.assertTrue(records[0]["confluence_H"])
        self.assertFalse(records[0]["confluence_L"])
        self.assertIsNone(records[0]["confluence_M"])
        summaries=confluence_rows(records)
        value=next(r for r in summaries if r["ema"]==20 and r["level"]=="H" and r["confluence_state"]=="yes" and r["event"]=="cloud_flip" and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertEqual((value["contacts"],value["known_events"],value["rate"]),(1,1,1))
        row["current"]=dict(known=False)
        records,_=contact_diagnostics([row],parent)
        self.assertIsNone(records[0]["cloud_flip"])
        value=next(r for r in confluence_rows(records) if r["ema"]==20 and r["level"]=="M" and r["confluence_state"]=="unknown" and r["event"]=="cloud_flip" and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertEqual((value["known_denominator"],value["unknown"],value["lower_bound"],value["upper_bound"]),(0,1,0,1))

    def test_extra_exposure_controls_share_mask_and_do_not_make_unknown_parent_zero(self):
        rows,parents,_=self.roster();rows=[]
        for i in parents:
            for p,m,v in [("BASE","parent_1",10),("BASE","parent_2",None if i=="unknown" else 20),("A20","diagnostic_1plus1",15),("A50","diagnostic_1plus1",15)]:
                rows.append(dict(episode_id=i,policy=p,mode=m,status="completed" if v is not None else "censored",net_dollars=v))
        saved=[r for r in exposure_control_rows(rows,parents) if r["policy"]=="A20" and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined"]
        self.assertEqual([r["complete_pairs"] for r in saved],[2,2])
        self.assertEqual([r["mean_difference"] for r in saved],[5,-5])
        self.assertEqual([r["individual_pairs"] for r in saved],[3,2])
        self.assertTrue(all(r["not_equal_risk"] for r in saved))

    def test_reclaim_after_unknown_is_known_but_first_time_censored(self):
        parent={"e":dict(direction=1,broker_day="2021-01-04")}
        def row(t,end,close,usable,contact=False):
            return dict(episode_id="e",time=f"2021-01-04T{t}:00Z",available_at=f"2021-01-04T{end}:00Z",close=close,high=close+1,low=99.9,contract="GC",usable=usable,open_position_landmark=True,parent_liquidation_net_unit=1,ema20_contact=contact,ema50_contact=False,ema20_frozen_level=100.05,ema20_contact_number=1)
        rows=[row("08:00","08:05",99.95,True,True),row("08:05","08:10",0,False),row("08:10","08:15",100.2,True)]
        records,_=contact_diagnostics(rows,parent)
        self.assertTrue(records[0]["reclaimed"])
        self.assertIsNone(records[0]["reclaim_at"])
        self.assertIsNone(records[0]["recovery_minutes"])
        self.assertEqual(records[0]["first_observed_reclaim_at"],"2021-01-04T08:15:00Z")

    def test_unmeasured_exposure_not_zero(self):
        rows,parents,_=self.roster()
        saved=risk_rows(rows,parents)
        base=next(r for r in saved if r["policy"]=="BASE" and r["mode"]=="parent_1" and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertIsNone(base["peak_notional"])
        half=next(r for r in saved if r["policy"]=="BASE" and r["mode"]=="half_parent" and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertEqual(half["peak_notional"],0)

    def test_unknown_episode_without_marks_breaks_equity_prefix(self):
        _,parents,_=self.roster()
        episodes=[dict(episode_id=i,policy="X1",mode="standardized",status="unknown" if i=="loss" else "completed",net_dollars=None if i=="loss" else 10,original_fills=0 if i=="loss" else 1) for i in parents]
        marks=[dict(policy="X1",mode="standardized",episode_id=i,time=parents[i]["entry_time"],closed_net_dollars=10,mtm_net_dollars=10,intraminute_mtm_min=0,intraminute_mtm_max=20,max_mtm_drawdown=10,active_quantity=0,notional=1000,concurrent_legs=1,combined_active_stop_risk=100) for i in ("win","unknown")]
        outcomes={(r["policy"],r["mode"],r["episode_id"]):r["net_dollars"] for r in episodes}
        path=list(stream_exposure_paths(marks,parents,outcomes))
        self.assertEqual([r["episode_id"] for r in path],["win"])
        rows=exposure_cohorts(marks,parents,episodes)
        allrow=next(r for r in rows if r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertIsNone(allrow["mtm_drawdown_dollars"])
        self.assertEqual(allrow["observed_prefix_mtm_drawdown_dollars"],10)
        self.assertEqual(allrow["observed_mtm_rows"],1)


if __name__=="__main__":unittest.main()
