"""Synthetic saved-record lineage checks; no market input or answer-source reads."""
from copy import deepcopy
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

STUDY=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

A=load("study29_saved_analysis_tests",STUDY/"phase4/analyze_saved_training.py")
M=load("study29_saved_analysis_model_tests",STUDY/"src/phase4_model.py")
DAY=date(2026,10,1)
CUT=M.P3.BASE.local(DAY,9,25)


def fixture():
    def reference(name,price,family,role):
        return M.Candidate(name,price,(price,price),family,role,"completed_RTH","rth",CUT-timedelta(days=1),
                           auction_id="rth",origin_role=name,source_identity="synthetic-only")
    candidates=(reference("YVAL",100,"VAL","value_boundary"),reference("YPOC",110,"POC","modal"),
                reference("YVAH",120,"VAH","value_boundary"),reference("ONPOC",110,"POC","modal"),
                reference("RTH_HIGH",130,"RTH_HIGH","range_extreme"))
    inputs=M.SelectionInputs(DAY,CUT,CUT-timedelta(minutes=5),CUT,97,candidates,(),True,True,input_identity="synthetic-only")
    return {"schema":"abacus.study29.phase4.local-training-map/v1","session_date":DAY.isoformat(),
            "selector_inputs":M.record(inputs),
            "selections":{p+"-"+d:M.record(M.select_map(inputs,pivot_policy=p,target_policy=d))
                          for p in ("P0","B0","B1") for d in ("D0","D1")}}


class SavedAnalysisTests(unittest.TestCase):
    def test_hydration_reproduces_saved_choices_without_selector_execution(self):
        document=fixture()
        with patch.object(M,"select_map",side_effect=AssertionError("must not recompute")):
            inputs,selections=A.hydrate_map(document,M)
        self.assertEqual(M.record(inputs),document["selector_inputs"])
        self.assertEqual(M.record(selections["P0-D1"]),document["selections"]["P0-D1"])

    def test_changed_selected_price_is_rejected_instead_of_inserted(self):
        document=fixture()
        document["selections"]["P0-D1"]["pivot"]["candidate"]["price"]=101
        with self.assertRaisesRegex(ValueError,"unchanged original candidate"):
            A.hydrate_map(document,M)

    def test_changed_group_member_cannot_masquerade_as_original_reference(self):
        document=fixture()
        document["selections"]["P0-D1"]["bullish"]["targets"][0]["group"][0]["source_identity"]="changed"
        with self.assertRaisesRegex(ValueError,"unchanged original candidate"):
            A.hydrate_map(document,M)

    def test_fallback_pivot_cannot_acquire_post_reveal_targets(self):
        document=fixture()
        document["selections"]["P0-D1"]["pivot"]["fallback"]=True
        with self.assertRaisesRegex(ValueError,"fallback pivot"):
            A.hydrate_map(document,M)

    def test_unknown_fields_missing_policy_and_cutoff_change_are_rejected(self):
        for change in ("unknown","missing-policy","cutoff"):
            document=fixture()
            if change=="unknown":document["selector_inputs"]["undocumented_feature"]=999
            elif change=="missing-policy":del document["selections"]["B0-D0"]
            else:document["selections"]["P0-D1"]["cutoff"]="2026-10-01T09:30:00-04:00"
            with self.subTest(change=change),self.assertRaises(ValueError):A.hydrate_map(document,M)

    def test_analysis_receives_sources_separately_and_keeps_frozen_pool(self):
        document=fixture()
        original=deepcopy(document)
        calls=[]
        def analyze(day,rows,inputs,selection,model):
            self.assertEqual(rows,[{"session_date":DAY.isoformat(),"source_price":999}])
            self.assertNotIn(999,[candidate.price for candidate in inputs.candidates])
            calls.append(selection.pivot.policy)
            return {"saved_only":True}
        with patch.object(M,"select_map",side_effect=AssertionError("must not recompute")):
            result=A.analyze_document(document,[{"session_date":DAY.isoformat(),"source_price":999}],M,
                                      SimpleNamespace(analyze_sources=analyze))
        self.assertEqual(len(calls),6)
        self.assertEqual(set(result),A.POLICIES)
        self.assertEqual(document,original)

    def test_naive_timestamp_and_nonfinite_coordinate_are_rejected(self):
        for changed in ("time","price"):
            document=fixture()
            if changed=="time":document["selector_inputs"]["cutoff"]="2026-10-01T09:25:00"
            else:document["selector_inputs"]["candidates"][0]["price"]=float("nan")
            with self.subTest(changed=changed),self.assertRaises(ValueError):A.hydrate_map(document,M)


if __name__=="__main__":unittest.main()
