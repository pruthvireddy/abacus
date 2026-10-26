import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

from phase3_publish_web import Draft,ReportSpec,SavedInputs,columns,filters,scalar,report_specs,guide_svg


class Phase3ProjectionTests(unittest.TestCase):
    def test_seven_conditions_and_nineteen_immutable_views(self):
        specs=report_specs()
        self.assertEqual(len(specs),19)
        self.assertEqual(len({s.group for s in specs}),7)
        self.assertEqual(len({s.publication_id for s in specs}),19)
        self.assertEqual([s.view for s in specs if s.group=="methods-risk"],["summary"])

    def test_distinct_three_timing_labels_and_usd_interval(self):
        for anchor,prefix in (("original_order_decision","Original order-decision"),("original_entry","Original entry-snapshot"),("actual_leg_fill","Actual leg-entry"),("EMA_decision_event","EMA event")):
            self.assertEqual(filters("sessions",anchor)[1]["label"],prefix+" session")
        self.assertEqual(columns(["mean_low"])[0]["unit"],"USD")
        self.assertNotIn("format",columns(["qualifies"])[0])

    def test_known_zero_blank_and_raw_strings_not_conflated(self):
        self.assertEqual(scalar("net_dollars","0"),0)
        self.assertIsNone(scalar("net_dollars",""))
        self.assertEqual(scalar("bucket","0"),"0")
        self.assertEqual(scalar("year","2026"),"2026")
        with self.assertRaises(ValueError):scalar("rate","nan")

    def test_exact_row_selection_and_nonadjacent_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory);(stage/"tables").mkdir()
            text="year,session,side,anchor,net_dollars\nall,all,combined,actual_leg_fill,0\n2020,London,long,actual_leg_fill,10\n2021,London,long,actual_leg_fill,\n"
            (stage/"tables/source.csv").write_text(text)
            d=Draft(SavedInputs(stage),"synthetic",ReportSpec("entry-gates","year"))
            copied=d.copy_table("tables/source.csv","tables/projection.csv",{"session":"London"})
            table=d.table("t","Saved rows",copied,columns(["year","session","side","net_dollars"],anchor="actual_leg_fill"),filters("year","actual_leg_fill"))
            self.assertEqual([r["c3"] for r in table["rows"]],[10,None])
            self.assertEqual(d.table_assertions[0]["columns"][3]["source_column"],"net_dollars")
            self.assertEqual(d.bindings[-1]["original_source_row"],2)
            self.assertEqual(d.table_assertions[0]["cohort_anchor_value"],"actual_leg_fill")
            self.assertEqual(d.sources[copied]["selected_source_rows"],[1,2])
            self.assertEqual((stage/"tables/source.csv").read_text(),text)

    def test_empty_copy_keeps_unknown_no_fabricated_row(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/"x.csv").write_text("year,net_dollars\n2020,\n")
            d=Draft(SavedInputs(p),"synthetic",ReportSpec("entry-gates","summary"))
            artifact=d.copy_table("x.csv","selected.csv",{"year":"2021"})
            self.assertEqual(d.copied_table(artifact),[])
            self.assertEqual(d.files[artifact],b"year,net_dollars\n")

    def test_illustration_is_labeled_and_references_confirmed_timing(self):
        from xml.etree import ElementTree
        text=" ".join(ElementTree.fromstring(guide_svg()).itertext())
        self.assertIn("Illustrative process only",text)
        self.assertIn("prior",text.lower())
        self.assertIn("next opening",text)
        self.assertIn("50% parent / 50% reserve",text)


if __name__=="__main__":unittest.main()
