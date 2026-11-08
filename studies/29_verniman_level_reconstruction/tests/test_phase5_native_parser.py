"""Synthetic captured-tooltip parsing; no actual market/answer source reads."""
from copy import deepcopy
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("study29_phase5_native_parser_tests", STUDY / "phase5/assemble_native_receipts.py")
N = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = N
SPEC.loader.exec_module(N)


def tip(lines):
    return "container common-tooltip-wrapper\n" + "\n".join("\t\t" + str(i + 100) + " text " + line for i,line in enumerate(lines)) + "\n\nThe focused UI element is 1 AXWebArea synthetic chart"


def candidate(identifier, price, *, target=False, reason="OWN_AUCTION_EXIT", members=None):
    lines=[identifier,f"Original price={price:.2f}; interval=[{price:.2f}, {price:.2f}]",
           "Family=VAH; role=value_boundary; window=Completed RTH",
           "Auction=synthetic-auction; parent=; side=; readyAt=2026-10-14 16:00"]
    if target:
        members=members or [identifier]
        lines.extend([f"Reason={reason}; originating={identifier}",f"Exact-price group has {len(members)} original IDs. No averaging."]+members)
    return tip(lines)


class TooltipParserTests(unittest.TestCase):
    def test_window_name_spaces_are_preserved_in_actual_identity(self):
        identifier="CME_MINI:ESZ2026:Completed RTH:synthetic:baseline:YVAH"
        result=N.parse_candidate(candidate(identifier,110,target=True),target=True)
        self.assertEqual(result["candidate_id"],identifier)
        self.assertEqual(result["window"],"Completed RTH")
        self.assertEqual(result["group_candidate_ids"],[identifier])

    def test_duplicate_price_groups_retain_all_ids_and_origin(self):
        identifier="CME_MINI:ESZ2026:Completed RTH:synthetic:baseline:RTH_HIGH"
        other="full:synthetic:baseline:FULL_HIGH"
        result=N.parse_candidate(candidate(identifier,110,target=True,members=[identifier,other]),target=True)
        self.assertEqual(result["group_count"],2)
        self.assertEqual(result["price"],110)
        self.assertEqual(result["originating_candidate_id"],identifier)

    def test_missing_target_stays_unavailable_without_an_invented_price(self):
        result=N.parse_candidate(tip(["FEWER_THAN_THREE_ELIGIBLE_DESTINATIONS; NO_ELIGIBLE_EXACT_CAUSAL_PBT"]),target=True)
        self.assertIsNone(result)
        with self.assertRaisesRegex(ValueError,"cannot be filled"):
            N.parse_candidate(tip(["FEWER_THAN_THREE_ELIGIBLE_DESTINATIONS"]),target=False)

    def test_unrecognized_missing_text_is_not_treated_as_valid_abstention(self):
        with self.assertRaisesRegex(ValueError,"cannot be filled"):
            N.parse_candidate(tip(["random empty tooltip"]),target=True)

    def test_original_price_must_lie_within_original_interval(self):
        text=candidate("full:synthetic:baseline:FULL_HIGH",110).replace("interval=[110.00, 110.00]","interval=[100.00, 101.00]")
        with self.assertRaisesRegex(ValueError,"invalid observed"):
            N.parse_candidate(text)

    def test_truncated_group_cannot_claim_full_identity_capture(self):
        identifier="full:synthetic:baseline:FULL_HIGH"
        text=candidate(identifier,110,target=True).replace("group has 1 original IDs","group has 17 original IDs")
        with self.assertRaisesRegex(ValueError,"group IDs missing"):
            N.parse_candidate(text,target=True)

    def test_origin_must_belong_to_original_exact_price_group(self):
        identifier="full:synthetic:baseline:FULL_HIGH"
        text=candidate(identifier,110,target=True).replace("originating="+identifier,"originating=not-a-member")
        with self.assertRaisesRegex(ValueError,"group IDs missing"):
            N.parse_candidate(text,target=True)

    def test_tooltip_wrapper_and_original_identity_are_required(self):
        with self.assertRaisesRegex(ValueError,"wrapper"):
            N.parse_candidate("Original price=110")
        with self.assertRaisesRegex(ValueError,"identity"):
            N.parse_candidate(candidate("some-model-value",110))


class ReceiptAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name).resolve()
        self.stage=self.root/"work/29_verniman_level_reconstruction/phase5_synthetic"
        self.evidence=self.stage/"native-evidence"
        self.evidence.mkdir(parents=True)
        self.day="2026-10-15"
        self.output=self.stage/"native-verification/2026-10-15.json"
        source=self.root/N.STUDY/"indicator/verniman_levels_phase4.pine"
        source.parent.mkdir(parents=True)
        shutil.copyfile(STUDY/"indicator/verniman_levels_phase4.pine",source)
        assembly=self.root/N.STUDY/"phase5/assemble_native_receipts.py"
        assembly.parent.mkdir(parents=True)
        shutil.copyfile(STUDY/"phase5/assemble_native_receipts.py",assembly)
        code_path=patch.object(N,"__file__",str(assembly))
        code_path.start();self.addCleanup(code_path.stop)
        readback=self.evidence/"readback.pine";shutil.copyfile(source,readback)
        settings=self.evidence/"settings.txt";settings.write_text("Synthetic settings inspection only\n")
        self.review={"schema":"abacus.study29.phase5.native-visual-review/v1","session_date":self.day,
            "settings":deepcopy(N.SETTINGS),"source_readback":N.pin(self.root,readback),"settings_evidence":N.pin(self.root,settings),"states":{}}
        for i,state in enumerate(("cutoff","advanced","restart")):
            picture=self.evidence/f"{self.day}-{state}.png";picture.write_bytes(b"synthetic evidence, not actual PNG")
            entries=[]
            for key in N.KEYS:
                if key=="pivot":text=candidate("CME_MINI:ESZ2026:Completed RTH:synthetic:baseline:YVAL",100)
                elif key=="bullish1":text=candidate("CME_MINI:ESZ2026:Completed RTH:synthetic:baseline:YVAH",110,target=True)
                elif key=="bearish1":text=candidate("full:synthetic:baseline:FULL_LOW",90,target=True,reason="RANGE_EXTREME")
                elif key=="pivot_status":text=tip(["none","synthetic confluence preserved"])
                else:text=tip(["FEWER_THAN_THREE_ELIGIBLE_DESTINATIONS; NO_ELIGIBLE_EXACT_CAUSAL_PBT"])
                path=self.evidence/f"{self.day}-{state}-{key}.txt";path.write_text("Synthetic AX header\n"+text)
                entries.append({"key":key,"path":str(path.relative_to(self.stage)),"tooltip":text})
            raw={"session_date":self.day,"state":state,"observed_at":f"2026-10-31T03:0{i}:00+00:00","screenshot":str(picture.relative_to(self.stage)),"tooltips":entries}
            (self.evidence/f"{self.day}-{state}-raw.json").write_text(json.dumps(raw))
            self.review["states"][state]={"screenshot":N.pin(self.root,picture),"cutoff":self.day+"T09:25:00-04:00",
                "last_included_open":self.day+"T09:20:00-04:00","last_included_close":self.day+"T09:25:00-04:00",
                "pivot":{"price":100,"reason_code":"P0_BELOW_VALUE_RECLAIM","status":"ready","native_display_status":"ready hypothesis","fallback":False},
                "bullish":{"status":"partial","prices":[110]},"bearish":{"status":"partial","prices":[90]},
                "cutoff_close":97,"buffer":2,"reference_count":20,"destination_group_count":4,"other_pivots":{"B0":105,"B1":100}}
        with (self.evidence/f"{self.day}-advanced.csv").open("w",newline="") as handle:
            writer=csv.writer(handle);writer.writerow(("time",));writer.writerows([(self.day+"T09:30:00-04:00",),(self.day+"T09:35:00-04:00",),(self.day+"T09:40:00-04:00",)])
        self.review_path=self.stage/"visual-review.json";self.save_review()

    def tearDown(self):self.temp.cleanup()

    def save_review(self):self.review_path.write_text(json.dumps(self.review))

    def assemble(self):return N.assemble(self.root,self.stage,self.review_path,self.output)

    def test_assembly_uses_only_native_text_and_visual_observations(self):
        result=self.assemble();self.assertTrue(result["native_state_invariance"])
        native=json.loads(self.output.read_text())
        self.assertFalse(native["local_prediction_fields_read"])
        self.assertEqual(native["states"]["advanced"]["latest_observed_bar_close"],self.day+"T09:40:00-04:00")
        self.assertEqual(len(native["states"]["cutoff"]["evidence"]),12)

    def test_visual_tooltip_disagreement_stops_before_receipt_creation(self):
        self.review["states"]["cutoff"]["bullish"]["prices"]=[111];self.save_review()
        with self.assertRaisesRegex(ValueError,"screenshot target"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_embedded_text_must_exist_in_actual_retained_capture(self):
        (self.evidence/f"{self.day}-cutoff-pivot.txt").write_text("stale different tooltip")
        with self.assertRaisesRegex(ValueError,"differs from retained"):
            self.assemble()

    def test_missing_screenshot_byte_pin_cannot_be_ignored(self):
        self.review["states"]["restart"]["screenshot"]["sha256"]="0"*64;self.save_review()
        with self.assertRaisesRegex(ValueError,"changed observed"):
            self.assemble()

    def test_native_ids_cannot_change_after_restart_at_same_price(self):
        raw_path=self.evidence/f"{self.day}-restart-raw.json";raw=json.loads(raw_path.read_text())
        item=next(t for t in raw["tooltips"] if t["key"]=="pivot")
        item["tooltip"]=item["tooltip"].replace("baseline:YVAL","baseline:changed")
        (self.stage/item["path"]).write_text(item["tooltip"]);raw_path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError,"changed across"):
            self.assemble()

    def test_protected_date_metadata_rejected_before_opening_native_files(self):
        self.review["session_date"]="2026-10-21";self.save_review()
        with self.assertRaisesRegex(ValueError,"authorized-date"):
            self.assemble()

    def test_refuses_overwriting_retained_native_receipt(self):
        self.assemble()
        with self.assertRaisesRegex(ValueError,"fresh native receipt"):
            self.assemble()

    def test_advance_uses_penultimate_bar_not_last_potentially_forming_bar(self):
        path=self.evidence/f"{self.day}-advanced.csv"
        result=N.conservative_advanced_close(path,self.day)
        self.assertEqual(result["penultimate_open"],self.day+"T09:35:00-04:00")
        self.assertEqual(result["last_exported_open"],self.day+"T09:40:00-04:00")
        self.assertEqual(result["latest_observed_bar_close"],self.day+"T09:40:00-04:00")

    def pivot_supplement(self, reason="P0_BELOW_VALUE_RECLAIM"):
        raw_path=self.evidence/f"{self.day}-cutoff-raw.json";raw=json.loads(raw_path.read_text())
        item=next(t for t in raw["tooltips"] if t["key"]=="pivot")
        original=N.tooltip_lines(item["tooltip"])
        item["tooltip"]=tip(["Maximum3 per branch. Partial ladders remain partial."])
        (self.stage/item["path"]).write_text(item["tooltip"])
        raw_path.write_text(json.dumps(raw))
        path=self.evidence/f"{self.day}-cutoff-selected-pivot-ledger.txt"
        path.write_text(tip([reason]+original))
        image=self.evidence/f"{self.day}-cutoff-selected-pivot-ledger.png";image.write_bytes(b"synthetic selected-row image")
        self.review["states"]["cutoff"]["pivot_capture_override"]={"format":"selected_pivot_ledger",
            "capture":N.pin(self.root,path),"screenshot":N.pin(self.root,image),
            "captured_at":"2026-10-31T03:00:30+00:00","captured_at_basis":"synthetic explicit timestamp"}
        self.save_review()

    def test_selected_ledger_supplement_recovers_actual_observation_and_keeps_failure(self):
        self.pivot_supplement()
        self.assemble()
        native=json.loads(self.output.read_text())
        state=native["states"]["cutoff"]
        self.assertEqual(state["observed_at"],"2026-10-31T03:00:30+00:00")
        self.assertEqual(state["raw_capture_completed_at"],"2026-10-31T03:00:00+00:00")
        self.assertEqual(len(state["evidence"]),14)
        self.assertTrue(state["pivot_capture_provenance"]["original_raw_capture_retained"])

    def test_ledger_alternative_cannot_be_called_the_selected_pivot(self):
        self.pivot_supplement("NOT_PRIMARY_PIVOT")
        with self.assertRaisesRegex(ValueError,"actual selected P0"):
            self.assemble()

    def test_supplement_hash_changes_are_rejected(self):
        self.pivot_supplement()
        self.review["states"]["cutoff"]["pivot_capture_override"]["capture"]["sha256"]="0"*64
        self.save_review()
        with self.assertRaisesRegex(ValueError,"changed observed"):
            self.assemble()


if __name__=="__main__":unittest.main()
