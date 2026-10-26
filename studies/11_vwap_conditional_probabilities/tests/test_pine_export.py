"""Checks for the presentation-only Pine export of sealed study 11."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPORT = ROOT / "reports/exports/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/20260925T034500Z_stats_only_v4"
SPEC = importlib.util.spec_from_file_location("vwap_pine_export", EXPORT / "generate.py")
assert SPEC and SPEC.loader
GEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN)
PRIOR_EXPORT = EXPORT.parent / "20260925T033700Z_conditional_pine_v3"
PRIOR_SPEC = importlib.util.spec_from_file_location("vwap_pine_export_v2", PRIOR_EXPORT / "generate.py")
assert PRIOR_SPEC and PRIOR_SPEC.loader
PRIOR_GEN = importlib.util.module_from_spec(PRIOR_SPEC)
PRIOR_SPEC.loader.exec_module(PRIOR_GEN)


def lookup_cells(generator: object) -> dict[str, str]:
    cells = {}
    cells.update(generator.a_lookup())
    cells.update(generator.race_lookup("question_b_outcomes.csv", "B", "geometry_bin"))
    cells.update(generator.race_lookup("question_c_outcomes.csv", "C", "position_bin"))
    cells.update(generator.update_lookup())
    return cells


class PineExportTests(unittest.TestCase):
    def test_stats_only_output_and_source_provenance(self) -> None:
        source = (EXPORT / GEN.SOURCE_NAME).read_text()
        output = (EXPORT / GEN.OUTPUT_NAME).read_text()
        self.assertEqual(GEN.sha256(EXPORT / GEN.SOURCE_NAME), GEN.EXPECTED_SOURCE_SHA256)
        self.assertIn('indicator("Session VWAP OE Scalp - Delta + TICK Bubbles"', source)
        self.assertIn('indicator("VWAP Conditional Stats · Study 11"', output)
        self.assertNotIn("Session VWAP OE Scalp", output)
        self.assertNotIn("request.footprint", output)
        self.assertNotIn("request.security(\"USI:TICK\"", output)
        self.assertNotIn("alertcondition(", output)
        self.assertNotIn("plotshape(", output)
        self.assertNotIn("fill(", output)
        self.assertEqual(len(re.findall(r"^plot\(", output, re.M)), 1)
        self.assertIn('plot(studyDayVwap, "Internal day VWAP (hidden)", display=display.none)', output)
        self.assertEqual(output.count('request.security_lower_tf(syminfo.tickerid, "1"'), 1)

    def test_saved_lookup_cells_and_sparse_suppression(self) -> None:
        cells = lookup_cells(GEN)
        self.assertEqual(len(cells), 123)
        self.assertEqual(cells["A|ES|1|2"].split("¦")[0], "30.6%")
        self.assertIn("1,475/4,823", cells["A|ES|1|2"])
        prior = lookup_cells(PRIOR_GEN)
        self.assertEqual(cells.keys(), prior.keys())
        for key in cells:
            self.assertEqual(cells[key].split("¦")[:2], prior[key].split("¦")[:2], key)
        for key, value in cells.items():
            display, support, tooltip = value.split("¦")
            self.assertTrue(support.startswith("n="), key)
            self.assertTrue(tooltip, key)
            if display == "SPARSE":
                self.assertNotIn("%", tooltip, key)
                self.assertIn("no rate displayed", tooltip)

    def test_rendered_keys_and_forecast_guards(self) -> None:
        output = (EXPORT / GEN.OUTPUT_NAME).read_text()
        self.assertEqual(len(re.findall(r'^        "(?:A|B|C|U10|U20)\|', output, re.M)), 123)
        self.assertGreater(output.count("f_study_lookup_"), 20)
        for block in re.findall(r"f_study_lookup_\d\d\(string key\) =>(.*?)(?=\nf_study_lookup|\Z)", output, re.S):
            self.assertLessEqual(len(re.findall(r'^        "(?:A|B|C|U10|U20)\|', block, re.M)), 6)
        self.assertNotIn("@STUDY_LOOKUP@", output)
        self.assertIn("if studyOn and studyChartOk and barstate.isconfirmed", output)
        self.assertIn("studyMinuteComplete", output)
        self.assertIn("studyHistoryComplete", output)
        self.assertIn('studyCState := "AMBIGUOUS"', output)
        self.assertIn('studyAState := "UNAVAILABLE"', output)
        self.assertIn("time_close + 30 * 60000", output)


if __name__ == "__main__":
    unittest.main()
