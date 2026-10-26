"""Saved-cell presentation boundaries, independent of numerical execution."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("study23_web", Path(__file__).resolve().parents[1] / "publish_web.py")
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


class PublicationCells(unittest.TestCase):
    def test_typed_cells_preserve_null_zero_negative_and_year_identity(self):
        self.assertIsNone(web.cell("net_dollars", ""))
        self.assertEqual(web.cell("net_dollars", "0"), 0.)
        self.assertEqual(web.cell("net_dollars", "-12.75"), -12.75)
        self.assertEqual(web.cell("completed", "0"), 0)
        self.assertEqual(web.cell("year", "2026"), "2026")
        self.assertIs(web.cell("partial_year", "False"), False)
        self.assertEqual(web.cell("bucket", "Monday"), "Monday")
        with self.assertRaises(ValueError):
            web.cell("net_dollars", "nan")

    def test_projection_keeps_exact_row_indices_all_cells_and_explicit_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder)
            (stage/"saved.csv").write_text("year,session,side,net_dollars\nall,all,combined,0\n2026,Outside,long,\n")
            evidence=web.Evidence(stage)
            rows=evidence.read("saved.csv")
            table=evidence.table("test", "Saved rows", "saved.csv", rows, ["year","session","side","net_dollars"], selected=[1,0])
            self.assertEqual(table["rows"], [rows[1],rows[0]])
            self.assertEqual([b["source_row"] for b in evidence.bindings], [1]*4+[0]*4)
            self.assertEqual(evidence.bindings[3]["value_type"], "null")
            self.assertEqual(evidence.bindings[7]["value_type"], "number")
            self.assertEqual([f["defaultValue"] for f in table["rowFilters"]], ["all","all","combined"])
            self.assertEqual(web.reference_id("inputs.lock.json"), "inputs-lock")

    def test_selected_evidence_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder)
            (stage/"real.csv").write_text("completed\n0\n")
            (stage/"saved.csv").symlink_to(stage/"real.csv")
            with self.assertRaises(ValueError):
                web.Evidence(stage).read("saved.csv")


if __name__=="__main__":
    unittest.main()
