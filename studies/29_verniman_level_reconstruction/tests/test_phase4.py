"""Hand-worked synthetic selection checks; no target/source/market-data reads."""
from dataclasses import replace
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src/phase4_model.py"
SPEC = importlib.util.spec_from_file_location("study29_phase4_tests", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
DAY = date(2026, 10, 1)
CUT = M.P3.BASE.local(DAY, 9, 25)


def candidate(identifier, price, family="HVE", role="edge", *, origin="", auction="", parent="", side="", ready=True, interval=None, **kwargs):
    return M.Candidate(identifier, price, (price, price) if interval is None else interval,
                       family, role, "synthetic-window", "synthetic-profile", CUT - timedelta(hours=1),
                       ready, auction, parent, side, origin, source_identity="synthetic-fixture", **kwargs)


def inputs(price=97, onpoc=110, extra=(), regions=()):
    refs = (candidate("ref/YVAH",120,"VAH","value_boundary",origin="YVAH",auction="rth"),
            candidate("ref/YPOC",110,"POC","modal",origin="YPOC",auction="rth"),
            candidate("ref/YVAL",100,"VAL","value_boundary",origin="YVAL",auction="rth"),
            candidate("ref/ONPOC",onpoc,"POC","modal",origin="ONPOC",auction="on"))
    return M.SelectionInputs(DAY,CUT,CUT-timedelta(minutes=5),CUT,price,refs+tuple(extra),tuple(regions),True,True,input_identity="synthetic-only")


def bars(start,end,price=110):
    opened=start
    while opened<end:
        yield M.P3.BASE.Bar(opened,opened+timedelta(minutes=5),price+1,price-1,price,100)
        opened+=timedelta(minutes=5)


class PivotTests(unittest.TestCase):
    def test_below_prior_value_selects_original_lower_boundary(self):
        result=M.select_pivot(inputs(97))
        self.assertEqual((result.price,result.reason_code,result.fallback),(100,"P0_BELOW_VALUE_RECLAIM",False))
        self.assertEqual(result.candidate.candidate_id,"ref/YVAL")

    def test_lower_and_upper_exact_tolerance_boundaries_are_within(self):
        for price in (98,122):
            with self.subTest(price=price):
                result=M.select_pivot(inputs(price,110))
                self.assertEqual((result.price,result.reason_code),(110,"P0_BALANCED_FALLBACK"))

    def test_value_migration_strict_boundaries(self):
        expected={107.75:(100,False),108:(110,True),112:(110,True),112.25:(120,False)}
        for onpoc,(price,fallback) in expected.items():
            with self.subTest(onpoc=onpoc):
                result=M.select_pivot(inputs(110,onpoc))
                self.assertEqual((result.price,result.fallback),(price,fallback))

    def test_unique_higher_auction_uses_original_lower_e1_and_interval(self):
        edge=candidate("on/node/lower",124,parent="node",auction="node",side="lower",interval=(122,126))
        region=M.Region("node",124,136,edge.candidate_id)
        result=M.select_pivot(inputs(130,extra=(edge,),regions=(region,)))
        self.assertEqual(result.price,124)
        self.assertEqual(result.candidate.interval,(122,126))
        self.assertFalse(result.fallback)
        self.assertEqual(result.reason_code,"P0_HIGHER_AUCTION_LOWER_E1")

    def test_higher_edge_exact_yvah_plus_buffer_is_ineligible(self):
        edge=candidate("on/edge",122,parent="node",side="lower")
        result=M.select_pivot(inputs(130,extra=(edge,),regions=(M.Region("node",122,140,edge.candidate_id),)))
        self.assertEqual((result.price,result.fallback_status),(120,"ABSENT"))

    def test_inclusive_shared_region_boundary_exposes_ambiguity(self):
        e1=candidate("a/lower",124,parent="a",side="lower")
        e2=candidate("b/lower",130,parent="b",side="lower")
        regions=(M.Region("a",124,130,e1.candidate_id),M.Region("b",130,140,e2.candidate_id,rank=2))
        result=M.select_pivot(inputs(130,extra=(e1,e2),regions=regions))
        self.assertTrue(result.fallback)
        self.assertEqual(result.fallback_status,"OVERLAP_OR_AMBIGUITY")

    def test_overlap_and_missing_neighbor_have_separate_fallbacks(self):
        edge=candidate("a/lower",124,parent="a",side="lower")
        for region,detail in ((M.Region("a",124,140,edge.candidate_id,overlap=True),"OVERLAP_OR_AMBIGUITY"),
                              (M.Region("a",124,140,None),"MISSING_EDGE")):
            with self.subTest(detail=detail):
                result=M.select_pivot(inputs(130,extra=(edge,),regions=(region,)))
                self.assertEqual(result.fallback_status,detail)

    def test_presentation_cap_does_not_silently_select_a_higher_auction(self):
        edge=candidate("a/lower",124,parent="a",side="lower")
        regions=[M.Region("a",124,140,edge.candidate_id)]
        regions.extend(M.Region(str(i),200+i*10,204+i*10,None,rank=i+1) for i in range(1,9))
        result=M.select_pivot(inputs(130,extra=(edge,),regions=regions))
        self.assertEqual((result.price,result.fallback_status),(120,"CAP"))

    def test_fixed_poc_and_nearest_value_baselines_have_exact_tie_rule(self):
        self.assertEqual(M.select_pivot(inputs(105),"B0").price,110)
        self.assertEqual(M.select_pivot(inputs(105),"B1").price,100)
        self.assertEqual(M.select_pivot(inputs(115),"B1").price,110)

    def test_baselines_share_required_coverage_even_if_formula_uses_fewer_inputs(self):
        for policy in ("P0","B0","B1"):
            result=M.select_pivot(replace(inputs(),overnight_ready=False),policy)
            self.assertIsNone(result.price)
            self.assertIn("OVERNIGHT_UNAVAILABLE",result.fallback_status)

    def test_missing_cutoff_close_and_missing_exact_terminal_abstain(self):
        for value in (replace(inputs(),cutoff_close=None),replace(inputs(),last_included_close=CUT-timedelta(minutes=5)),
                      replace(inputs(),last_included_open=None)):
            self.assertEqual(M.select_pivot(value).status,"unavailable")

    def test_noncontrol_cutoff_and_later_value_reference_abstain(self):
        late=replace(inputs(),cutoff=CUT+timedelta(minutes=5),last_included_open=CUT,last_included_close=CUT+timedelta(minutes=5))
        self.assertIn("NONCONTROL_CUTOFF",M.select_pivot(late).fallback_status)
        original=inputs()
        refs=tuple(replace(c,ready_at=CUT+timedelta(seconds=1)) if c.origin_role=="YPOC" else c for c in original.candidates)
        self.assertEqual(M.select_pivot(replace(original,candidates=refs)).status,"unavailable")

    def test_duplicate_required_reference_identity_is_ambiguous(self):
        original=inputs()
        self.assertEqual(M.select_pivot(replace(original,candidates=original.candidates+(original.candidates[0],))).status,"unavailable")

    def test_backadjusted_price_coordinates_are_not_silently_labeled_unadjusted(self):
        value=replace(inputs(),adjustment="continuous_backadjusted")
        selected=M.select_pivot(value)
        self.assertEqual(selected.status,"unavailable")
        self.assertIn("UNSUPPORTED_ADJUSTMENT_CONVENTION",selected.fallback_status)
        self.assertIn(("adjustment","continuous_backadjusted"),selected.explanatory_inputs)

    def test_foreign_contract_required_reference_cannot_enter_map(self):
        original=inputs()
        refs=tuple(replace(c,contract="ESH2027") if c.origin_role=="YPOC" else c for c in original.candidates)
        self.assertEqual(M.select_pivot(replace(original,candidates=refs)).status,"unavailable")

    def test_foreign_contract_edge_is_not_reported_as_confluence(self):
        current=candidate("current/edge",101)
        foreign=candidate("foreign/edge",101,contract="ESH2027")
        result=M.select_pivot(inputs(97,extra=(current,foreign)))
        self.assertEqual(result.price,100)
        self.assertEqual(result.confluence_ids,("current/edge",))

    def test_confluence_preserves_distinct_edge_prices_and_selected_price(self):
        edge=candidate("nearby/edge",101,interval=(99,103))
        result=M.select_pivot(inputs(97,extra=(edge,)))
        self.assertEqual(result.price,100)
        self.assertEqual(result.confluence_ids,("nearby/edge",))


class TargetTests(unittest.TestCase):
    def test_structural_exit_precedes_nearer_intervening_boundary(self):
        extra=(candidate("interior",108),candidate("range/near",125,"RTH_HIGH","range_extreme"),candidate("range/far",132,"ONH","range_extreme"))
        value=inputs(extra=extra)
        bull,bear=M.select_targets(value,M.select_pivot(value))
        self.assertEqual([t.candidate.price for t in bull.targets],[120,125,132])
        self.assertEqual([t.reason_code for t in bull.targets],["OWN_AUCTION_EXIT","RANGE_EXTREME","RANGE_EXTREME"])
        self.assertTrue(any(a.candidate_id=="interior" and a.reason=="INTERVENING_REFERENCE_SKIPPED_BY_STRUCTURAL_PRIORITY" for a in bull.alternatives))
        self.assertEqual(bear.status,"partial")

    def test_distance_baseline_is_explicit_price_order_and_spacing(self):
        extra=(candidate("e1",105),candidate("e2",107),candidate("e3",108),candidate("e4",116))
        value=inputs(extra=extra)
        bull,_=M.select_targets(value,M.select_pivot(value),"D0")
        self.assertEqual([t.candidate.price for t in bull.targets],[105,108,116])
        self.assertTrue(all(t.reason_code=="DISTANCE_BASELINE" for t in bull.targets))
        self.assertTrue(any(a.candidate_id=="e2" and a.reason=="SPACING" for a in bull.alternatives))

    def test_bearish_order_is_strictly_descending(self):
        extra=(candidate("range95",95,"ONL","range_extreme"),candidate("range90",90,"RTH_LOW","range_extreme"),candidate("e85",85))
        value=inputs(extra=extra)
        _,bear=M.select_targets(value,M.select_pivot(value))
        self.assertEqual([t.candidate.price for t in bear.targets],[95,90,85])
        self.assertEqual([t.rank for t in bear.targets],[1,2,3])

    def test_upper_value_pivot_has_own_auction_exit_on_bearish_side(self):
        value=inputs(110,113,extra=(candidate("inside",115),candidate("low90",90,"ONL","range_extreme")))
        pivot=M.select_pivot(value)
        self.assertEqual(pivot.price,120)
        _,bear=M.select_targets(value,pivot)
        self.assertEqual([t.candidate.price for t in bear.targets],[100,90])
        self.assertEqual(bear.targets[0].reason_code,"OWN_AUCTION_EXIT")

    def test_selected_lower_node_edge_uses_qualified_same_parent_upper_edge(self):
        lower=candidate("lower",124,parent="a",auction="a",side="lower",interval=(122,126))
        upper=candidate("upper",140,parent="a",auction="a",side="upper",interval=(138,142))
        value=inputs(130,extra=(lower,upper),regions=(M.Region("a",124,140,"lower","upper"),))
        bull,_=M.select_targets(value,M.select_pivot(value))
        self.assertEqual(bull.targets[0].originating_candidate_id,"upper")
        self.assertEqual(bull.targets[0].candidate.interval,(138,142))

    def test_missing_opposite_edge_does_not_invent_target(self):
        lower=candidate("lower",124,parent="a",auction="a",side="lower")
        value=inputs(130,extra=(lower,),regions=(M.Region("a",124,140,"lower"),))
        bull,_=M.select_targets(value,M.select_pivot(value))
        self.assertEqual(bull.targets,())
        self.assertEqual(bull.status,"partial")

    def test_exact_duplicate_prices_retain_all_roles_without_averaging(self):
        value=inputs(extra=(candidate("000edge",120),candidate("range130",130,"ONH","range_extreme")))
        bull,_=M.select_targets(value,M.select_pivot(value))
        target=bull.targets[0]
        self.assertEqual(target.candidate.candidate_id,"000edge")
        self.assertEqual(target.candidate.price,120)
        self.assertEqual([c.candidate_id for c in target.group],["000edge","ref/YVAH"])
        self.assertEqual(target.originating_candidate_id,"ref/YVAH")
        self.assertEqual(len({t.candidate.price for t in bull.targets}),len(bull.targets))

    def test_overlapping_uncertainty_intervals_with_different_prices_are_not_merged(self):
        value=inputs(extra=(candidate("e105",105,interval=(101,109)),candidate("e108",108,interval=(104,112))))
        bull,_=M.select_targets(value,M.select_pivot(value),"D0")
        self.assertEqual([t.candidate.price for t in bull.targets],[105,108,120])

    def test_fallback_pivot_abstains_both_target_branches(self):
        value=inputs(110,110,extra=(candidate("extra",140),))
        for policy in ("D0","D1"):
            bull,bear=M.select_targets(value,M.select_pivot(value),policy)
            self.assertEqual((bull.status,bear.status),("unavailable","unavailable"))
            self.assertEqual(bull.targets,())
            self.assertEqual(bull.reasons,("PIVOT_FALLBACK_TARGET_ABSTENTION",))

    def test_modal_unsupported_later_and_foreign_candidates_are_not_destinations(self):
        extra=(candidate("hvn",105,"HVN","modal"),candidate("gap",106,"GAP","unsupported"),
               replace(candidate("late",107),ready_at=CUT+timedelta(seconds=1)),
               candidate("foreign",108,contract="ESH2027"))
        value=inputs(extra=extra)
        bull,_=M.select_targets(value,M.select_pivot(value),"D0")
        self.assertEqual([t.candidate.price for t in bull.targets],[120])
        reasons={a.candidate_id:a.reason for a in bull.alternatives}
        self.assertIn("gap",reasons)
        self.assertIn("foreign",reasons)
        self.assertIn("late",reasons)

    def test_supported_causal_point_pbt_is_allowed_but_interval_and_identity_are_not(self):
        extra=(candidate("pbt-point",150,"PBT","projection"),
               candidate("pbt-interval",160,"PBT","projection",interval=(158,162)),
               candidate("pbt-identity",170,"PBT","projection",identity_projection=True))
        value=inputs(extra=extra)
        bull,_=M.select_targets(value,M.select_pivot(value))
        self.assertEqual([t.candidate.price for t in bull.targets],[120,150])
        self.assertTrue(any(a.candidate_id=="pbt-interval" and a.reason=="NONEXACT_PBT" for a in bull.alternatives))
        self.assertTrue(any(a.candidate_id=="pbt-identity" and a.reason=="IDENTITY_NOT_EXTERNAL" for a in bull.alternatives))

    def test_range_extremes_precede_nearer_external_boundaries_in_d1(self):
        value=inputs(extra=(candidate("range140",140,"ONH","range_extreme"),candidate("external130",130),candidate("external150",150)))
        bull,_=M.select_targets(value,M.select_pivot(value))
        self.assertEqual([t.candidate.price for t in bull.targets],[120,140,150])
        self.assertNotIn(130,[t.candidate.price for t in bull.targets])

    def test_cap_and_missing_branches_are_explicit(self):
        extra=tuple(candidate(f"r{i}",i,"ONH","range_extreme") for i in (125,130,135,140))
        value=inputs(extra=extra)
        bull,bear=M.select_targets(value,M.select_pivot(value))
        self.assertEqual(len(bull.targets),3)
        self.assertTrue(any(a.reason=="TARGET_CAP" for a in bull.alternatives))
        self.assertEqual(bear.status,"partial")
        self.assertIn("NO_ELIGIBLE_EXACT_CAUSAL_PBT",bear.reasons)


class AdapterAndFreezeTests(unittest.TestCase):
    def history(self, day=DAY):
        previous=M.P3.BASE.prior_trading_date(day)
        return list(bars(M.P3.BASE.local(previous-timedelta(days=1),18),M.P3.BASE.local(previous,17)))+list(bars(M.P3.BASE.local(day-timedelta(days=1),18),M.P3.BASE.local(day,9,25)))

    def test_adapter_retains_baseline_ids_prices_and_optional_missing_week(self):
        engine=M.P3.Phase3Engine()
        engine.feed(self.history())
        adapted=M.inputs_from_phase3(engine.expanded_snapshot,110)
        self.assertTrue(adapted.rth_ready)
        self.assertTrue(adapted.overnight_ready)
        yval=next(c for c in adapted.candidates if c.origin_role=="YVAL")
        self.assertEqual(yval.price,engine.snapshot.values[10])
        self.assertIn("baseline:YVAL",yval.candidate_id)
        weekly=[c for c in adapted.candidates if c.window=="previous_completed_week"]
        self.assertTrue(all(not c.ready for c in weekly))
        self.assertEqual(M.select_pivot(adapted).status,"ready")

    def test_adapter_retains_and_rejects_actual_nonfrozen_adjustment(self):
        engine=M.Phase4Engine(adjustment="continuous_backadjusted")
        engine.feed(self.history())
        adapted=M.inputs_from_phase3(engine.expanded_snapshot,110)
        self.assertEqual(adapted.adjustment,"continuous_backadjusted")
        self.assertEqual(engine.selection_snapshot.pivot.status,"unavailable")

    def test_missing_expected_prior_weekday_does_not_use_older_observed_rth(self):
        engine=M.Phase4Engine()
        engine.feed(self.history(date(2026,9,29)))
        engine.feed(bars(M.P3.BASE.local(DAY-timedelta(days=1),18),CUT))
        self.assertEqual(engine.selection_snapshot.pivot.status,"unavailable")
        self.assertIn("PRIOR_EXPECTED_RTH_UNAVAILABLE",engine.selection_snapshot.pivot.fallback_status)

    def test_after_cutoff_bars_and_anchor_changes_cannot_mutate_frozen_choices(self):
        engine=M.Phase4Engine()
        engine.feed(self.history())
        frozen=engine.selection_snapshot
        before=M.record(frozen)
        engine.anchors["C"]="later-unsupported-mutation"
        engine.feed(bars(CUT,M.P3.BASE.local(DAY,11),price=999))
        self.assertIs(engine.selection_snapshot,frozen)
        self.assertEqual(M.record(engine.selection_snapshot),before)

    def test_identical_history_restart_reproduces_all_decision_fields(self):
        first,second=M.Phase4Engine(),M.Phase4Engine()
        first.feed(self.history());second.feed(self.history())
        self.assertEqual(M.record(first.selection_snapshot),M.record(second.selection_snapshot))

    def test_new_trading_date_resets_preopen_selection(self):
        engine=M.Phase4Engine()
        engine.feed(self.history())
        next_day=DAY+timedelta(days=1)
        engine.feed(bars(M.P3.BASE.local(next_day-timedelta(days=1),18),M.P3.BASE.local(next_day-timedelta(days=1),18,5)))
        self.assertIsNone(engine.selection_snapshot)

    def test_no_terminal_bar_means_no_late_substitute(self):
        engine=M.Phase4Engine()
        history=self.history()[:-1]
        engine.feed(history)
        engine.feed(bars(CUT,M.P3.BASE.local(DAY,9,35)))
        self.assertIsNone(engine.selection_snapshot)

    def test_json_projection_contains_no_live_reference_or_datetime_object(self):
        result=M.record(M.select_map(inputs()))
        encoded=json.dumps(result,allow_nan=False)
        self.assertIn("phase4-4.0.0",encoded)
        self.assertEqual(result["cutoff"],CUT.isoformat())


class EvaluationTests(unittest.TestCase):
    def source(self,identifier="source",family="YVAL",price=100,window="synthetic-profile"):
        matching=M._matching_module()
        return matching.SourceReference(identifier,DAY.isoformat(),"daily-plan","revision1",(family,),
                                        (price,price),window,"ESZ2026","individual_contract_unadjusted")

    def test_generator_failure_and_selection_failure_are_distinct(self):
        value=inputs()
        selected=M.select_map(value)
        sources=[self.source("exists-but-not-selected","YVAH",120),self.source("not-generated","HVE",140)]
        result=M.evaluate_role(value,selected,sources,role="pivot")
        self.assertEqual({row["source_id"]:row["status"] for row in result["source_outcomes"]},
                         {"exists-but-not-selected":"SELECTION_FAILURE","not-generated":"CANDIDATE_GENERATION_FAILURE"})

    def test_supported_pivot_match_preserves_point_error_and_null_source_availability(self):
        value=inputs()
        result=M.evaluate_role(value,M.select_map(value),[self.source(price=100.5)],role="pivot")
        self.assertEqual(result["source_outcomes"][0]["status"],"END_TO_END_SUPPORTED_ROLE_MATCH")
        self.assertEqual(result["selected_matches_conditional_on_generated_candidate"],1)
        self.assertIsNone(result["source_outcomes"][0]["source_historical_available_at"])
        self.assertEqual(result["selection"]["strata"][0]["assignments"][0]["interval_gap_points"],"0.5")

    def test_unknown_window_is_descriptive_not_zero_primary_coverage(self):
        value=inputs()
        result=M.evaluate_role(value,M.select_map(value),[self.source(window=None)],role="pivot")
        self.assertEqual(result["status"],"not_estimable")
        self.assertIsNone(result["selection"]["primary_role_coverage"])
        self.assertTrue(result["generation"]["unresolved_alternatives"])
        self.assertEqual(result["source_outcomes"][0]["status"],"UNRESOLVED_IDENTITY_OR_UNSUPPORTED_FAMILY")

    def test_unsupported_adjustment_cannot_produce_strict_matching_claims(self):
        value=replace(inputs(),adjustment="continuous_backadjusted")
        result=M.evaluate_role(value,M.select_map(value),[self.source()],role="pivot")
        self.assertEqual(result["status"],"not_executed")
        self.assertIsNone(result["generation"]["qualified_generated_count"])
        self.assertIn("UNSUPPORTED_ADJUSTMENT_CONVENTION",result["map_unavailable_reasons"])
        self.assertEqual(result["source_outcomes"][0]["status"],"GENERATOR_UNAVAILABLE")

    def test_unavailable_generator_does_not_report_zero_candidates(self):
        result=M.evaluate_role(None,None,[self.source()],role="pivot")
        self.assertEqual(result["status"],"not_executed")
        self.assertIsNone(result["generation"]["qualified_generated_count"])
        self.assertIsNone(result["physical_selected_count"])

    def test_fallback_is_abstention_not_a_target_selection_failure(self):
        value=inputs(110,110)
        result=M.evaluate_role(value,M.select_map(value),[self.source("upper","YVAH",120)],role="bullish",source_order={"upper":1})
        self.assertEqual(result["source_outcomes"][0]["status"],"SELECTOR_ABSTENTION")
        self.assertTrue(result["selector_abstained"])

    def test_source_ladder_beyond_cap_is_retained_and_not_complete(self):
        extra=tuple(candidate(f"edge/{price}",price) for price in (105,108,115,125))
        value=inputs(extra=extra)
        selected=M.select_map(value,target_policy="D0")
        sources=[self.source(f"s{rank}","HVE",price) for rank,price in enumerate((105,108,115,125),1)]
        result=M.evaluate_role(value,selected,sources,role="bullish",source_order={f"s{i}":i for i in range(1,5)})
        self.assertEqual(result["ordering"][0]["observed_target_count"],4)
        self.assertFalse(result["ordering"][0]["complete_ladder_agreement"])
        self.assertEqual(len(result["source_outcomes"]),4)

    def test_exact_duplicate_group_counts_once_within_same_family_and_window(self):
        value=inputs(extra=(candidate("a",105),candidate("b",105)))
        sources=[self.source("s1","HVE",105),self.source("s2","HVE",105)]
        result=M.evaluate_role(value,M.select_map(value,target_policy="D0"),sources,role="bullish")
        self.assertEqual(result["selection"]["matched_occurrence_count"],1)
        self.assertEqual(sum(row["status"]=="AMBIGUOUS_ONE_TO_ONE_COMPETITION" for row in result["source_outcomes"]),1)

    def test_evaluation_never_inserts_missing_source_price_into_candidates(self):
        value=inputs()
        original=tuple(c.price for c in value.candidates)
        M.evaluate_role(value,M.select_map(value),[self.source("unseen","HVE",999)],role="pivot")
        self.assertEqual(tuple(c.price for c in value.candidates),original)
        self.assertNotIn(999,original)


if __name__=="__main__":
    unittest.main()
