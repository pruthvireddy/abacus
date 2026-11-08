"""Synthetic future schedules and role maps only; no market or answer inputs."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); sys.modules[name] = result
    spec.loader.exec_module(result); return result


G = module("study29_phase6_test_gate", STUDY / "phase6/reveal_gate.py")
S = module("study29_phase6_test_score", STUDY / "phase6/score_saved.py")
M = module("study29_phase6_test_model", STUDY / "src/phase4_model.py")
H = module("study29_phase6_test_hydrator", STUDY / "phase4/analyze_saved_training.py")
C = module("study29_phase6_test_comparison", STUDY / "phase4/run_training.py")
W = module("study29_phase6_test_windows", STUDY / "phase5/window_identity.py")


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dates = [(date(2030, 1, 2) + timedelta(days=i)).isoformat() for i in range(20)]
        self.end = datetime(2030, 1, 21, 21, tzinfo=timezone.utc)
        self.now = self.end + timedelta(minutes=1)
        self.freeze = {"schema": "abacus.study29.phase6.freeze/v1", "scheduled_dates": self.dates,
            "frozen_at": "2029-12-20T00:00:00+00:00", "period_end_at": self.end.isoformat(), "files": [], "producer_files": []}
        self.write("freeze.json", self.freeze)
        self.access = {"schema": "abacus.study29.phase6.access-log/v1", "closed_through": self.now.isoformat(),
            "complete_to_best_knowledge": True, "actors": [{"actor_id": "synthetic-predictor", "role": "prediction"},
                {"actor_id": "synthetic-collector", "role": "collector"}], "events": []}
        self.write("access.json", self.access)
        self.ledger = {"schema": "abacus.study29.phase6.session-ledger/v1", "protocol_freeze": self.pin("freeze.json"), "sessions": []}
        for i, day in enumerate(self.dates):
            self.write(f"map-{i}.json", {"session_date": day, "synthetic_complete_map": True})
            self.write(f"capture-{i}.json", {"schema": "abacus.study29.phase6.capture/v1", "session_date": day,
                "status": "timely", "protocol_freeze": self.pin("freeze.json"), "prediction": self.pin(f"map-{i}.json"),
                "operator_id": "synthetic-predictor", "captured_at": day + "T14:26:00+00:00", "complete_expanded_map": True,
                "source_access_log": self.pin("access.json"), "incomplete_reasons": []})
            self.ledger["sessions"].append({"session_date": day, "status": "timely", "receipt": self.pin(f"capture-{i}.json"),
                "finalized_at": day + "T14:27:00+00:00", "incomplete_reasons": []})
        self.write("ledger.json", self.ledger)

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value, sort_keys=True))

    def pin(self, name):
        return G.pin(self.root, self.root / name)

    def refresh_receipt(self, index, **changes):
        name = f"capture-{index}.json"; receipt = G.load(self.root / name); receipt.update(changes)
        self.write(name, receipt); self.ledger["sessions"][index]["receipt"] = self.pin(name)
        self.write("ledger.json", self.ledger)

    def check(self):
        return G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "access.json",
            now=self.now, capture_validator=lambda *a, **k: {"synthetic_validator": "passed"})

    def test_complete_batch_releases_only_after_period(self):
        result = self.check(); self.assertTrue(result["reveal_allowed"]); self.assertEqual(result["complete_timely_count"], 20)

    def test_no_early_reveal(self):
        self.now = self.end - timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError, "period has not ended"): self.check()

    def test_pending_session_is_incomplete(self):
        self.ledger["sessions"][0]["status"] = "pending"; self.write("ledger.json", self.ledger)
        with self.assertRaisesRegex(ValueError, "incomplete batch"): self.check()

    def test_cannot_delete_scheduled_failure(self):
        self.ledger["sessions"].pop(); self.write("ledger.json", self.ledger)
        with self.assertRaisesRegex(ValueError, "every scheduled"): self.check()

    def test_missing_placeholder_not_complete_map(self):
        self.refresh_receipt(0, status="missing")
        self.ledger["sessions"][0]["status"] = "missing"; self.write("ledger.json", self.ledger)
        with self.assertRaisesRegex(ValueError, "must not masquerade"): self.check()

    def test_explicit_missing_retained_after_period(self):
        self.refresh_receipt(0, status="missing", prediction=None, complete_expanded_map=False, incomplete_reasons=["synthetic missing input"])
        self.ledger["sessions"][0]["status"] = "missing"; self.write("ledger.json", self.ledger)
        result = self.check(); self.assertEqual(result["complete_timely_count"], 19)
        self.assertEqual(result["missing_or_input_unavailable_dates"], [self.dates[0]])

    def test_changed_prediction_rejected(self):
        self.write("map-0.json", {"tampered": True})
        with self.assertRaisesRegex(ValueError, "changed"): self.check()

    def test_wrong_date_rejected(self):
        self.refresh_receipt(0, session_date="2030-02-01")
        with self.assertRaisesRegex(ValueError, "ledger day"): self.check()

    def test_stale_final_audit_rejected(self):
        self.now = self.end + timedelta(minutes=10)
        self.access["closed_through"] = (self.now - timedelta(minutes=6)).isoformat(); self.write("final-access.json", self.access)
        with self.assertRaisesRegex(ValueError, "five minutes"):
            G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "final-access.json", now=self.now, capture_validator=lambda *a, **k: {})

    def test_future_audit_closure_rejected(self):
        self.access["closed_through"] = (self.now + timedelta(seconds=1)).isoformat(); self.write("final-access.json", self.access)
        with self.assertRaisesRegex(ValueError, "future"):
            G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "final-access.json", now=self.now, capture_validator=lambda *a, **k: {})

    def test_placeholder_actor_rejected(self):
        self.access["actors"][0]["actor_id"] = "pending"; self.write("final-access.json", self.access)
        with self.assertRaisesRegex(ValueError, "placeholders"):
            G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "final-access.json", now=self.now, capture_validator=lambda *a, **k: {})

    def test_later_exposure_keeps_original_receipt_and_effective_exposed_status(self):
        event = {"event_id": "synthetic-breach", "actor_id": "synthetic-predictor", "kind": "answer_access", "session_date": self.dates[0], "occurred_at": self.dates[0] + "T14:25:00+00:00"}
        final = deepcopy(self.access); final["events"].append(event); self.write("final-access.json", final)
        for row in self.ledger["sessions"]: row["status"] = "exposed"
        self.write("ledger.json", self.ledger)
        result = G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "final-access.json", now=self.now, capture_validator=lambda *a, **k: {})
        self.assertTrue(result["batch_blinding_breach"]); self.assertFalse(result["formal_prospective_estimation_allowed"])
        self.assertEqual(result["captures"][0]["original_receipt_status"], "timely")

    def test_exposure_cannot_stay_timely(self):
        final = deepcopy(self.access); final["events"] = [{"event_id": "breach", "actor_id": "synthetic-predictor", "kind": "answer_access", "session_date": self.dates[0], "occurred_at": self.dates[0] + "T14:25:00+00:00"}]; self.write("final-access.json", final)
        with self.assertRaisesRegex(ValueError, "effective exposure"):
            G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "final-access.json", now=self.now, capture_validator=lambda *a, **k: {})

    def test_exposure_between_period_end_and_gate_is_breach(self):
        final = deepcopy(self.access); final["events"] = [{"event_id": "between-end-gate", "actor_id": "synthetic-predictor", "kind": "answer_access", "session_date": self.dates[0], "occurred_at": (self.end + timedelta(seconds=15)).isoformat()}]; self.write("final-access.json", final)
        result = G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "final-access.json", now=self.now, capture_validator=lambda *a, **k: {})
        self.assertTrue(result["batch_blinding_breach"])

    def test_collector_access_does_not_expose_prediction_actor(self):
        final = deepcopy(self.access); final["events"] = [{"event_id": "collector-only", "actor_id": "synthetic-collector", "kind": "answer_access", "session_date": self.dates[0], "occurred_at": self.dates[0] + "T14:20:00+00:00"}]; self.write("final-access.json", final)
        result = G.check_gate(self.root, self.root / "freeze.json", self.root / "ledger.json", self.root / "final-access.json", now=self.now, capture_validator=lambda *a, **k: {})
        self.assertFalse(result["batch_blinding_breach"])

    def test_finalization_cannot_predate_capture(self):
        self.ledger["sessions"][0]["finalized_at"] = self.dates[0] + "T14:25:00+00:00"; self.write("ledger.json", self.ledger)
        with self.assertRaisesRegex(ValueError, "before its saved receipt"): self.check()


def synthetic_map(day="2030-01-02"):
    d = date.fromisoformat(day); cutoff = M.P3.BASE.local(d, 9, 25); prior = cutoff - timedelta(days=1)
    candidates = []
    for identifier, price, family, role in (("YVAL",100,"VAL","value_boundary"),("YPOC",110,"POC","modal"),("YVAH",120,"VAH","value_boundary"),("ONPOC",105,"POC","modal"),("ONH",130,"ONH","range_extreme"),("ONL",90,"ONL","range_extreme")):
        candidates.append(M.Candidate(identifier,price,(price,price),family,role,"completed_RTH","synthetic-rth",prior,True,auction_id="synthetic-rth",origin_role=identifier,source_identity="synthetic-only"))
    inputs = M.SelectionInputs(d,cutoff,cutoff-timedelta(minutes=5),cutoff,97,tuple(candidates),(),True,True,input_identity="synthetic-only")
    return {"schema":"abacus.study29.phase6.local-map/v1","session_date":day,"selector_inputs":M.record(inputs),"selections":{p+"-"+t:M.record(M.select_map(inputs,pivot_policy=p,target_policy=t)) for p in ("P0","B0","B1") for t in ("D0","D1")}}


def source_row(identifier="trigger-bullish", side="bullish", role="pivot", price="100", order=None, revision="synthetic-r1", day="2030-01-02"):
    return {"level_id":identifier,"session_date":day,"source_class":"named_daily_plan","provenance":{"source_revision_id":revision},"families":["YVAL"],"price_low":price,"price_high":price,"actual_contract":"ESZ26","source_timing_class":"synthetic_unknown","available_at":None,"phase4_role":S.ROLES[role],"source_target_order":order,"scenario_side":side,"original_label":"synthetic YVAL "+price,"directional_conditions":"unmeasured synthetic","comparison":{"unsupported_or_unresolved_roles":[]}}


class SavedScoringTests(unittest.TestCase):
    def analyze(self, rows, document=None):
        document = document or synthetic_map()
        assessments = {row["level_id"]:{"status":"unidentified_no_explicit_window_metadata"} for row in rows}
        return S.analyze_saved(document,rows,M,H,C,W,assessments,[document["session_date"]])

    def test_deterministic_saved_only_scoring_without_selector(self):
        document = synthetic_map(); before = deepcopy(document)
        rows = [source_row(),source_row("trigger-bearish",side="bearish"),source_row("bull-t1",role="bullish",price="120",order=1)]
        with patch.object(M,"select_map",side_effect=AssertionError("never rerun")):
            first = self.analyze(rows,document); second = self.analyze(rows,document)
        self.assertEqual(first,second); self.assertEqual(document,before)

    def test_unknown_window_is_not_estimable(self):
        result = self.analyze([source_row(),source_row("bear",side="bearish")])
        strict = result["P0-D1"]["pivot"]["strict_decomposition"]
        self.assertEqual(strict["status"],"not_estimable")
        self.assertIsNone(strict["selected_matches_conditional_on_generated_candidate"])

    def test_conflicting_revisions_not_nearest_selected(self):
        rows = [source_row(r+side,side=side,price=price,revision=r) for r,price in (("r1","100"),("r2","102")) for side in ("bullish","bearish")]
        result = self.analyze(rows)
        self.assertEqual(result["P0-D1"]["pivot"]["primary_pivot_interpretation"]["status"],"unresolved_single_pivot_ground_truth")

    def test_source_targets_beyond_three_cap_retained(self):
        rows = [source_row("target"+str(i),role="bullish",price=str(120+i*5),order=i) for i in range(1,6)]
        result = self.analyze(rows)
        self.assertEqual(result["P0-D1"]["bullish"]["coordinate_only_diagnostic"]["source_count"],5)

    def test_wrong_map_date_rejected(self):
        with self.assertRaisesRegex(ValueError,"scheduled date"):
            S.hydrate_saved(synthetic_map(),M,H,["2030-02-01"])

    def test_mutated_selected_coordinate_rejected(self):
        document = synthetic_map(); document["selections"]["P0-D1"]["pivot"]["candidate"]["price"] = 999
        with self.assertRaisesRegex(ValueError,"unchanged original"):
            S.hydrate_saved(document,M,H,[document["session_date"]])

    def test_missing_configuration_rejected(self):
        document = synthetic_map(); document["selections"].pop("B0-D0")
        with self.assertRaisesRegex(ValueError,"all six"):
            S.hydrate_saved(document,M,H,[document["session_date"]])

    def test_no_eligible_denominator_not_zero_percent(self):
        result = S.summarize([],sorted(S.POLICIES))
        self.assertEqual(result["P0-D1"]["roles"]["pivot"]["eligible_date_count"],0)
        self.assertIsNone(result["P0-D1"]["roles"]["pivot"]["pivot_actual_point_error"]["mean_absolute"])
        self.assertIsNone(result["P0-D1"]["end_to_end_observable_map"]["interval_reproduction_wilson95"])
        self.assertFalse(result["P0-D1"]["validated_method"])

    def test_minimum_and_abstention_do_not_force_validation(self):
        diagnostic={"source_count":2,"matched_count":0,"selected_count":0,"complete_coordinate_ladder":None,"assignments":[]}
        analysis={p:{role:{"coordinate_only_diagnostic":deepcopy(diagnostic)} for role in S.ROLES} for p in S.POLICIES}
        records=[{"session_date":str(i),"formal_role_eligibility":{role:True for role in S.ROLES},"canonical_analysis":analysis} for i in range(15)]
        result=S.summarize(records,sorted(S.POLICIES))["P0-D1"]
        self.assertEqual(result["formal_estimation_status"],"minimum_met_estimation_only")
        self.assertEqual(result["roles"]["bullish"]["source_misses"],30)
        self.assertEqual(result["roles"]["bullish"]["ordering_undefined_or_abstained"],15)
        self.assertFalse(result["validated_method"])

    def test_exposed_batch_formal_minimum_disallowed(self):
        diagnostic={"source_count":1,"matched_count":1,"selected_count":1,"complete_coordinate_ladder":True,"assignments":[]}
        analysis={p:{role:{"coordinate_only_diagnostic":deepcopy(diagnostic)} for role in S.ROLES} for p in S.POLICIES}
        records=[{"session_date":str(i),"formal_role_eligibility":{role:True for role in S.ROLES},"canonical_analysis":analysis} for i in range(20)]
        result=S.summarize(records,sorted(S.POLICIES),formal_batch_allowed=False)["P0-D1"]
        self.assertEqual(result["formal_estimation_status"],"descriptive_only_insufficient_or_exposed_sample")

    def test_interval_touch_is_not_actual_boundary_ladder(self):
        d={"source_count":1,"matched_count":1,"selected_count":1,"complete_coordinate_ladder":True,"assignments":[{"signed_point_or_boundary_error":"2"}]}
        analysis={p:{role:{"coordinate_only_diagnostic":deepcopy(d)} for role in S.ROLES} for p in S.POLICIES}
        record={"session_date":"synthetic","formal_role_eligibility":{role:True for role in S.ROLES},"canonical_analysis":analysis}
        result=S.summarize([record],sorted(S.POLICIES))["P0-D1"]
        self.assertEqual(result["roles"]["bullish"]["complete_ordered_ladders"],1)
        self.assertEqual(result["roles"]["bullish"]["actual_point_or_boundary_complete_ladders"],0)
        self.assertEqual(result["end_to_end_observable_map"]["actual_point_or_boundary_reproductions"],0)

    def test_unreadable_intervals_remain_unreadable(self):
        self.assertFalse(S.readable_interval({"price_low":None,"price_high":None}))
        self.assertFalse(S.readable_interval({"price_low":"NaN","price_high":"NaN"}))
        self.assertFalse(S.readable_interval({"price_low":"2","price_high":"1"}))

    def test_common_end_to_end_needs_own_minimum(self):
        d={"source_count":1,"matched_count":0,"selected_count":0,"complete_coordinate_ladder":None,"assignments":[]}
        analysis={p:{role:{"coordinate_only_diagnostic":deepcopy(d)} for role in S.ROLES} for p in S.POLICIES}
        records=[]
        for i in range(20):
            eligibility={role: i not in set(range(j*5,j*5+5)) for j,role in enumerate(S.ROLES)}
            records.append({"session_date":str(i),"formal_role_eligibility":eligibility,"canonical_analysis":analysis})
        result=S.summarize(records,sorted(S.POLICIES))["P0-D1"]
        self.assertTrue(all(r["minimum_met"] for r in result["roles"].values()))
        self.assertEqual(result["end_to_end_observable_map"]["date_denominator"],5)
        self.assertFalse(result["end_to_end_observable_map"]["minimum_met"])

    def test_no_preopen_proof_cannot_choose_favorable_canonical(self):
        row=source_row(); sessions={row["session_date"]:{"canonical_source_revision_ids":["synthetic-r1"]}}
        with self.assertRaisesRegex(ValueError,"no authenticated"):
            S.validate_canonical_revisions([row],sessions,{row["level_id"]:{"supported":False}})

    def test_earliest_independent_preopen_revision_required(self):
        first=source_row("first",revision="r1"); later=source_row("later",revision="r2")
        preopen={"first":{"supported":True,"captured_at":"2030-01-02T14:00:00+00:00"},"later":{"supported":True,"captured_at":"2030-01-02T14:10:00+00:00"}}
        with self.assertRaisesRegex(ValueError,"earliest"):
            S.validate_canonical_revisions([first,later],{first["session_date"]:{"canonical_source_revision_ids":["r2"]}},preopen)

    def test_tied_preopen_revisions_remain_conflicting(self):
        first=source_row("first",revision="r1"); other=source_row("other",revision="r2")
        preopen={key:{"supported":True,"captured_at":"2030-01-02T14:00:00+00:00"} for key in ("first","other")}
        S.validate_canonical_revisions([first,other],{first["session_date"]:{"canonical_source_revision_ids":["r1","r2"]}},preopen)

    def test_paired_errors_use_same_date_and_remain_comparator_minus_primary(self):
        first={"source_count":1,"matched_count":1,"selected_count":1,"pivot_absolute_point_or_boundary_error":"2","complete_coordinate_ladder":None}
        second={**first,"matched_count":0,"pivot_absolute_point_or_boundary_error":"5"}
        record={"session_date":"synthetic","formal_role_eligibility":{"pivot":True},"canonical_analysis":{"P0-D1":{"pivot":{"coordinate_only_diagnostic":first}},"B0-D0":{"pivot":{"coordinate_only_diagnostic":second}}}}
        result=S.paired_differences([record],["P0-D1","B0-D0"])["B0-D0"]["pivot"]
        self.assertEqual(result["paired_date_count"],1)
        self.assertEqual(result["mean_comparator_minus_primary_absolute_point_or_boundary_error"],3)
        self.assertEqual(result["per_session"][0]["comparator_minus_primary_coordinate_pairs"],-1)

    def test_paired_zero_denominator_is_null(self):
        result=S.paired_differences([],["P0-D1","B1-D1"])["B1-D1"]["pivot"]
        self.assertIsNone(result["mean_comparator_minus_primary_absolute_point_or_boundary_error"])

    def test_autopivot_alternate_is_separate_saved_pivot_not_target(self):
        document=synthetic_map();document["autopivot_comparator"]={"frozen":{"selection":{"price":100}},"alternate_model_only":{"price":120,"is_target":False},"pine_sha256":"synthetic-pine","model_sha256":"synthetic-model"}
        rows=[source_row(),source_row("bear",side="bearish")]
        analysis=self.analyze(rows,document)
        result=S.autopivot_diagnostics(document,analysis,rows,C,M)
        self.assertFalse(result["is_target"])
        self.assertEqual(result["diagnostics"]["primary"]["matched_count"],1)
        self.assertEqual(result["diagnostics"]["alternate"]["matched_count"],0)

    def test_far_autopivot_miss_retains_actual_placement_error(self):
        document=synthetic_map();document["autopivot_comparator"]={"frozen":{"selection":{"price":150}},"alternate_model_only":{"price":80,"is_target":False}}
        rows=[source_row(),source_row("bear",side="bearish")]
        result=S.autopivot_diagnostics(document,self.analyze(rows,document),rows,C,M)
        self.assertEqual(result["diagnostics"]["primary"]["matched_count"],0)
        self.assertEqual(result["diagnostics"]["primary"]["pivot_signed_point_or_boundary_error"],"50")
        self.assertEqual(result["diagnostics"]["primary"]["pivot_interval_gap_points"],"50")
        self.assertEqual(result["diagnostics"]["alternate"]["pivot_absolute_point_or_boundary_error"],"20")


class PreopenEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.evidence=self.root/"collector";self.evidence.mkdir()
        (self.evidence/"source.json").write_text('{"synthetic":"full same revision"}')
        self.row=source_row();self.row.update(collector_actor_id="synthetic-collector",source_access_event_ids=["source-event"],available_at="2030-01-02T14:00:00+00:00")
        self.access={"actors":[{"actor_id":"synthetic-collector","role":"collector"}],"events":[{"event_id":"source-event","actor_id":"synthetic-collector","kind":"answer_access","session_date":self.row["session_date"],"source_class":"named_daily_plan","source_revision_id":"synthetic-r1","occurred_at":"2030-01-02T14:00:00+00:00"}]}
        self.proof={"schema":"abacus.study29.phase6.source-availability-evidence/v1","session_date":self.row["session_date"],"source_class":"named_daily_plan","source_revision_id":"synthetic-r1","same_revision_authenticated":True,"complete_plan_capture":True,"timestamp_basis":"contemporaneous_browser_capture_local_clock","captured_at":"2030-01-02T14:00:00+00:00","available_at":self.row["available_at"],"source_artifact":G.pin(self.root,self.evidence/"source.json"),"collector_actor_id":"synthetic-collector","source_access_event_id":"source-event"}
        self.cutoff=G.aware("2030-01-02T14:25:00+00:00")

    def assess(self):
        path=self.evidence/"proof.json";path.write_text(json.dumps(self.proof));self.row["preopen_availability_evidence"]=G.pin(self.root,path)
        return S.preopen_support(self.row,self.root,self.evidence,self.access,self.cutoff)

    def test_contemporaneous_evidence_is_locally_qualified(self):
        result=self.assess();self.assertTrue(result["supported"]);self.assertFalse(result["independent_timestamp_certification_claimed"])

    def test_displayed_timestamp_alone_not_preopen(self):
        self.proof["timestamp_basis"]="displayed_post_timestamp"
        self.assertFalse(self.assess()["supported"])

    def test_late_capture_not_preopen(self):
        self.proof["captured_at"]="2030-01-02T14:26:00+00:00"
        self.assertFalse(self.assess()["supported"])

    def test_null_availability_not_repaired(self):
        self.row["available_at"]=None
        self.assertFalse(self.assess()["supported"])

    def test_wrong_revision_not_preopen(self):
        self.proof["source_revision_id"]="different-revision"
        self.assertFalse(self.assess()["supported"])

    def test_access_after_capture_rejected(self):
        self.access["events"][0]["occurred_at"]="2030-01-02T14:01:00+00:00"
        self.assertFalse(self.assess()["supported"])

    def test_incomplete_crop_not_preopen_full_plan(self):
        self.proof["complete_plan_capture"]=False
        self.assertFalse(self.assess()["supported"])

    def test_claimed_independent_timestamp_requires_certificate(self):
        self.proof["timestamp_basis"]="independently_timestamped_capture"
        self.assertFalse(self.assess()["supported"])


class CaptureGateIntegrationTests(unittest.TestCase):
    def test_actual_status_receipts_do_not_masquerade_as_complete_predictions(self):
        fixtures=module("study29_phase6_gate_capture_fixture",STUDY/"tests/test_phase6_capture.py")
        fixture=fixtures.CaptureFixtures();fixture.setUp();self.addCleanup(fixture.tearDown)
        captures=fixtures.C
        sessions=[]
        for index,day in enumerate(fixture.freeze["scheduled_dates"]):
            current=captures.at(day,"09:31").astimezone(timezone.utc)
            access=deepcopy(fixture.access);access["closed_through"]=(current-timedelta(seconds=1)).isoformat()
            access_path=fixture.stage/f"missing-access-{index}.json";fixtures.dump(access_path,access)
            request={"schema":"abacus.study29.phase6.status-request/v1","session_date":day,"status":"missing","incomplete_reasons":["synthetic absent daily capture"],"operator_id":"predictor-A","source_access_log":captures.pinned(fixture.root,access_path)}
            request_path=fixture.stage/f"missing-request-{index}.json";fixtures.dump(request_path,request)
            output=fixture.stage/f"missing-{index}"
            with patch.object(captures,"construct_map",side_effect=AssertionError("status verification must never construct a map")):
                receipt=captures.finalize_status(fixture.root,fixture.freeze_path,request_path,output,now=current)
            sessions.append({"session_date":day,"status":"missing","receipt":captures.pinned(fixture.root,output/"capture-receipt.json"),"finalized_at":receipt["captured_at"],"incomplete_reasons":receipt["incomplete_reasons"]})
        now=captures.at(fixture.freeze["scheduled_dates"][-1],"16:01").astimezone(timezone.utc)
        final_access=deepcopy(fixture.access);final_access["closed_through"]=now.isoformat()
        final_path=fixture.stage/"final-access.json";fixtures.dump(final_path,final_access)
        ledger={"schema":"abacus.study29.phase6.session-ledger/v1","protocol_freeze":captures.pinned(fixture.root,fixture.freeze_path),"sessions":sessions}
        ledger_path=fixture.stage/"ledger.json";fixtures.dump(ledger_path,ledger)
        result=G.check_gate(fixture.root,fixture.freeze_path,ledger_path,final_path,now=now)
        self.assertEqual(result["complete_timely_count"],0)
        self.assertEqual(len(result["missing_or_input_unavailable_dates"]),20)
        self.assertEqual(result["evaluation_status"],"incomplete_or_exposed_evaluation_retained")


if __name__ == "__main__": unittest.main()
