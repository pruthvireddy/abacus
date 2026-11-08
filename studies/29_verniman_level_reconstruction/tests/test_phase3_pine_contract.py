"""Pine source-preservation guards, not Pine compilation or numeric execution."""
import hashlib
from pathlib import Path
import re
import unittest

STUDY = Path(__file__).resolve().parents[1]


def retained_baseline(derivative: str) -> tuple[str, str]:
    retained, additions = [], []
    inside = False
    for line in derivative.splitlines():
        if line.strip().startswith("// PHASE3 BEGIN"):
            if inside:
                raise ValueError("nested Phase3 markers")
            inside = True
        elif line.strip() == "// PHASE3 END":
            if not inside:
                raise ValueError("unpaired Phase3 end marker")
            inside = False
        elif inside:
            additions.append(line)
        else:
            retained.append(line)
    if inside:
        raise ValueError("unclosed Phase3 block")
    return "\n".join(retained), "\n".join(additions)


def normalize_spacing(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


class PinePreservationTests(unittest.TestCase):
    def test_original_verified_phase1_bytes_remain_exact(self):
        self.assertEqual(hashlib.sha256((STUDY / "indicator/verniman_levels.pine").read_bytes()).hexdigest(),
                         "5bbc40075cefb19feacb1a676c67ee5770cb5ef7023b9dd76781f2927a243f73")

    def test_additive_blocks_leave_original_baseline_source(self):
        original = (STUDY / "indicator/verniman_levels.pine").read_text()
        derivative = (STUDY / "indicator/verniman_levels_phase3.pine").read_text()
        retained, additions = retained_baseline(derivative)
        retained = retained.replace(", max_boxes_count=32", "")
        retained = retained.replace(
            "// Phase 3 v3.0.0: experimental N1/E1/composite/manual P1/P2 candidates.\n"
            "// Phase 1 baseline arithmetic retained; no LIS/pivot or ordered target selection.\n"
            "// Not Verniman’s recovered algorithms; see ../phase3/protocol.md.",
            "// Phase 1: approximate candidate references only. See ../specification.md.\n"
            "// No HVE/HVN/LVN detector, PBT projection, LIS or target selection is implemented.")
        self.assertEqual(normalize_spacing(retained), normalize_spacing(original))
        self.assertTrue(additions)

    def test_new_hooks_do_not_mutate_existing_baseline_state(self):
        _, additions = retained_baseline((STUDY / "indicator/verniman_levels_phase3.pine").read_text())
        baseline_variables = ("full", "rth", "overnight", "week", "live", "frozen", "priorWeek", "priorRth",
                              "priorFullH", "priorFullL", "fullSource", "rthSource", "weekSource", "currentId",
                              "frozenAt", "frozenLastOpen", "frozenFullSource", "frozenRthSource",
                              "frozenWeekSource", "snapshotAttempted", "snapshotExact", "processedClose")
        for variable in baseline_variables:
            with self.subTest(variable=variable):
                self.assertIsNone(re.search(r"(?m)^\s*" + variable + r"(?:\.[\w.]+)?\s*:=", additions))
                self.assertIsNone(re.search(r"\b" + variable + r"\.(?:reset|ingest|clear|add)\(", additions))
                self.assertIsNone(re.search(r"array\.(?:set|fill|clear|push|pop|shift|unshift)\(\s*" + variable + r"\s*[,)]", additions))
