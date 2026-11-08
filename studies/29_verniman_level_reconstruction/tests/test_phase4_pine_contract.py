"""Byte/source guards only; these neither compile Pine nor execute Replay."""
import hashlib
from pathlib import Path
import re
import unittest

STUDY = Path(__file__).resolve().parents[1]
INDICATOR = STUDY / "indicator"


def strip_phase4(source):
    retained, additions = [], []
    inside = False
    for line in source.splitlines():
        if line.strip().startswith("// PHASE4 BEGIN"):
            if inside:
                raise ValueError("nested Phase4 source marker")
            inside = True
        elif line.strip() == "// PHASE4 END":
            if not inside:
                raise ValueError("unpaired Phase4 source marker")
            inside = False
        elif inside:
            additions.append(line)
        else:
            retained.append(line)
    if inside:
        raise ValueError("unclosed Phase4 source block")
    return "\n".join(retained), "\n".join(additions)


def normalize_blank_runs(value):
    return re.sub(r"\n{3,}", "\n\n", value).strip()+"\n"


class Phase4PineSourceGuards(unittest.TestCase):
    def test_original_candidate_revisions_remain_exact_retained_bytes(self):
        identities = {
            "verniman_levels_phase3.pine": "9cf9f9a56311496ea7414758d1dd51e6e9a7af5739cffa4438c35190b1f64504",
            "verniman_levels_phase3_3_0_1.pine": "40b28d3a581edc1246582f9d2c4c7b127f24423885ba16d20c1cfb65f8b294cd",
            "verniman_levels_phase3_3_0_2.pine": "034c3731f2ada4620aac9a80ca20261d0a06376bee044fa30e95529ad9e1954c",
        }
        for name, expected in identities.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((INDICATOR/name).read_bytes()).hexdigest(),expected)

    def test_stripping_additions_restores_exact_candidate_backend_302(self):
        original = (INDICATOR/"verniman_levels_phase3_3_0_2.pine").read_text()
        retained, additions = strip_phase4((INDICATOR/"verniman_levels_phase4.pine").read_text())
        retained = retained.replace("// Phase 3 backend implementation 3.0.2", "// Phase 3 implementation 3.0.2")
        self.assertEqual(normalize_blank_runs(retained),normalize_blank_runs(original))
        self.assertTrue(additions)

    def test_selection_additions_do_not_write_baseline_or_candidate_state(self):
        _, additions = strip_phase4((INDICATOR/"verniman_levels_phase4.pine").read_text())
        inherited=("full","rth","overnight","week","live","frozen","priorWeek","priorRth",
                   "priorFullH","priorFullL","fullSource","rthSource","weekSource","currentId",
                   "frozenAt","frozenLastOpen","frozenFullSource","frozenRthSource","frozenWeekSource",
                   "snapshotAttempted","snapshotExact","processedClose","p3Completed","p3PreviousWeek",
                   "p3Frozen","p3FrozenCandidates","p3FrozenAnchors","p3FrozenProjections")
        for name in inherited:
            with self.subTest(name=name):
                self.assertIsNone(re.search(r"(?m)^\s*"+name+r"(?:\.[\w.]+)?\s*:=",additions))
                self.assertIsNone(re.search(r"\b"+name+r"\.(?:reset|ingest|clear|add)\(",additions))
                self.assertIsNone(re.search(r"array\.(?:set|fill|clear|push|pop|shift|unshift)\(\s*"+name+r"\s*[,)]",additions))
        for formal_input in ("baseline","profiles","ledgers","projections"):
            self.assertIsNone(re.search(r"array\.(?:set|fill|clear|push|pop|shift|unshift)\(\s*"+formal_input+r"\s*[,)]",additions))

    def test_declared_objects_fit_source_derived_maximum_allocation(self):
        source=(INDICATOR/"verniman_levels_phase4.pine").read_text()
        declaration=next(line for line in source.splitlines() if line.startswith("indicator("))
        line_limit=int(re.search(r"max_lines_count=(\d+)",declaration).group(1))
        label_limit=int(re.search(r"max_labels_count=(\d+)",declaration).group(1))
        box_limit=int(re.search(r"max_boxes_count=(\d+)",declaration).group(1))
        # Forty-one inherited slots + sixteen E1 + three PBT + pivot and six targets.
        self.assertGreaterEqual(line_limit,41+16+3+1+3+3)
        self.assertGreaterEqual(label_limit,41+16+3+1+3+3)
        self.assertGreaterEqual(box_limit,8+7+3)
        self.assertIn("var array<line> p4Lines = array.new_line(7, na)",source)
        self.assertIn("var array<label> p4Labels = array.new_label(7, na)",source)

    def test_documented_compiler_and_contract_fixes_are_explicit_backend_identity(self):
        source=(INDICATOR/"verniman_levels_phase3_3_0_2.pine").read_text()
        self.assertIn('string P3_IMPLEMENTATION = "3.0.2"',source)
        self.assertIn('string P3_POLICY = "P3-3.0.0-N1E1-P1-P2"',source)
        self.assertIn("string P3_CONTRACT = ticker.standard(syminfo.tickerid)",source)
        self.assertIn('string rawChartContext = ""',source)
        self.assertIn("a.contract != P3_CONTRACT",source)
        self.assertIn("string cellText, string tip",source)
        self.assertIn("float zoneLow =",source)
        self.assertIn("float zoneHigh =",source)


if __name__=="__main__":
    unittest.main()
