"""Execute the delivered Pine's scalar helpers against independent expectations.

This deliberately small translator is NOT a TradingView compiler. It exercises
the actual signal, cooldown, entry/path-validity and excursion helper bodies;
series state, UDT arrays, chart feeds, drawing and runtime limits need Pine
Editor/replay verification. No historical study is run by this suite.
"""

from pathlib import Path
import math
import random
import re
from types import SimpleNamespace
import unittest


PINE = Path(__file__).resolve().parents[1] / "pine/vwap_oe_fade_stats.pine"
SOURCE = PINE.read_text()


def helper(name):
    lines = SOURCE.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(name + "("))
    signature = lines[start].split("(", 1)[1].rsplit(")", 1)[0]
    args = [item.strip().split()[-1] for item in signature.split(",")]
    body = []
    for line in lines[start + 1:]:
        if line and not line.startswith(" "):
            break
        statement = line.split("//", 1)[0].rstrip()
        if not statement.strip():
            continue
        statement = re.sub(r"^(\s*)(?:bool|int|float) ", r"\1", statement)
        statement = statement.replace(":=", "=").replace("else if ", "elif ")
        statement = re.sub(r"\btrue\b", "True", statement)
        statement = re.sub(r"\bfalse\b", "False", statement)
        statement = re.sub(r"\bna\(", "_missing(", statement)
        statement = re.sub(r"\bna\b", "None", statement)
        if statement.lstrip().startswith(("if ", "elif ")) or statement.strip() == "else":
            statement += ":"
        body.append(statement)
    if not body or not body[-1].startswith("    ") or body[-1].startswith("        "):
        raise ValueError("Expected final base-indented expression")
    body[-1] = "    return " + body[-1].strip()
    namespace = {
        "math": SimpleNamespace(max=max),
        "_missing": lambda v: v is None or (isinstance(v, float) and math.isnan(v)),
    }
    exec("def " + name + "(" + ", ".join(args) + "):\n" + "\n".join(body), namespace)
    return namespace[name]


DIRECTION = helper("fadeDirection")
ACCEPT = helper("fadeAccept")
ENTRY = helper("fadeEntryAllowed")
PATH = helper("fadePathValid")
EXCURSIONS = helper("fadeExcursions")


class FadeHelpersTest(unittest.TestCase):
    def test_strict_two_sigma_and_fade_direction(self):
        for price, expected in [(97.99, 1), (98.0, 0), (100.0, 0), (102.0, 0), (102.01, -1)]:
            self.assertEqual(DIRECTION(price, 100.0, 1.0, False, False, None, None, None), expected)

    def test_no_signal_when_sigma_or_vwap_unavailable(self):
        for sigma in (None, float("nan"), 0.0, -1.0):
            self.assertEqual(DIRECTION(90.0, 100.0, sigma, False, False, None, None, None), 0)
        self.assertEqual(DIRECTION(90.0, None, 1.0, False, False, None, None, None), 0)

    def test_every_close_and_fresh_cross_differ(self):
        self.assertEqual(DIRECTION(97, 100, 1, False, True, 97, 100, 1), 1)
        self.assertEqual(DIRECTION(97, 100, 1, True, True, 97, 100, 1), 0)
        self.assertEqual(DIRECTION(97, 100, 1, True, True, 98, 100, 1), 1)
        self.assertEqual(DIRECTION(103, 100, 1, True, True, 102, 100, 1), -1)

    def test_cross_uses_previous_bands_not_current_band_for_previous_close(self):
        self.assertEqual(DIRECTION(97, 100, 1, True, True, 96, 97, 1), 1)
        self.assertEqual(DIRECTION(103, 100, 1, True, True, 104, 103, 1), -1)
        self.assertEqual(DIRECTION(97, 100, 1, True, False, 99, 100, 1), 0)

    def test_all_five_independent_cooldowns(self):
        for cooldown in (0, 5, 10, 20, 30):
            last = -1000000
            accepted = []
            for i in range(71):
                if ACCEPT(True, i, last, cooldown):
                    accepted.append(i)
                    last = i
            self.assertEqual(accepted, list(range(0, 71, cooldown + 1)))

    def test_rejected_signal_does_not_restart_cooldown(self):
        last = 10
        for i in range(11, 21):
            self.assertFalse(ACCEPT(True, i, last, 10))
        self.assertTrue(ACCEPT(True, 21, last, 10))
        self.assertFalse(ACCEPT(False, 21, last, 10))

    def test_next_open_only_excludes_signal_candle(self):
        self.assertFalse(ENTRY(1, 120000, 1000000, 0, 120000, True, True, True))
        self.assertTrue(ENTRY(1, 120000, 1000000, 120000, 240000, True, True, True))
        self.assertFalse(ENTRY(1, 120000, 1000000, 240000, 360000, True, True, True))
        self.assertFalse(ENTRY(0, 120000, 1000000, 120000, 240000, True, True, True))

    def test_missing_or_partial_entry_never_gets_filled_later(self):
        for contiguous, full in [(False, True), (True, False), (False, False)]:
            self.assertFalse(ENTRY(-1, 120000, 1000000, 120000, 240000, contiguous, full, True))

    def test_session_end_equality_and_cross_session_option(self):
        self.assertTrue(ENTRY(1, 120000, 240000, 120000, 240000, True, True, True))
        self.assertFalse(ENTRY(1, 240000, 240000, 240000, 360000, True, True, True))
        self.assertTrue(ENTRY(1, 240000, 240000, 240000, 360000, True, True, False))
        self.assertTrue(PATH(240000, 240000, True, True, True))
        self.assertFalse(PATH(360000, 240000, True, True, True))
        self.assertTrue(PATH(360000, 240000, True, True, False))
        self.assertFalse(PATH(360000, 240000, False, True, False))

    def test_long_and_short_arithmetic(self):
        self.assertEqual(EXCURSIONS(1, 100, 97, 108, 104), [8, 3, 4])
        self.assertEqual(EXCURSIONS(-1, 100, 97, 108, 104), [3, 8, -4])
        self.assertEqual(EXCURSIONS(1, 100, 100, 100, 100), [0, 0, 0])

    def test_entry_reference_and_signal_extremes_are_different(self):
        # Signal may have had high 120/low 80/close 110. None belongs to the
        # next-open path, whose actual entry is 112 after an opening gap.
        self.assertEqual(EXCURSIONS(-1, 112, 108, 115, 109), [4, 3, 3])

    def test_random_paths_against_direct_directional_offsets(self):
        rng = random.Random(1501)
        for _ in range(500):
            entry = rng.uniform(1, 10000)
            path = [entry] + [entry + rng.uniform(-50, 50) for _ in range(100)]
            for direction in (-1, 1):
                offsets = [direction * (p - entry) for p in path]
                expected = [max(offsets), -min(offsets), offsets[-1]]
                actual = EXCURSIONS(direction, entry, min(path), max(path), path[-1])
                for x, y in zip(actual, expected):
                    self.assertAlmostEqual(x, y)

    def test_extrema_monotonic_on_identical_event_cohort(self):
        path = [100, 103, 98, 104, 101, 96, 109]
        for direction in (-1, 1):
            results = [EXCURSIONS(direction, 100, min(path[:n]), max(path[:n]), path[n-1]) for n in range(1, len(path)+1)]
            for before, after in zip(results, results[1:]):
                self.assertGreaterEqual(after[0], before[0])
                self.assertGreaterEqual(after[1], before[1])

    def test_partial_path_support_is_per_horizon_not_failure(self):
        end = 12 * 120000
        supported = [h for h in (5, 10, 15, 20, 30, 50, 100) if PATH(h * 120000, end, True, True, True)]
        self.assertEqual(supported, [5, 10])

    def test_translation_does_not_change_excursions(self):
        base = EXCURSIONS(-1, 100, 96, 109, 102)
        shifted = EXCURSIONS(-1, 5100, 5096, 5109, 5102)
        self.assertEqual(base, shifted)


if __name__ == "__main__":
    unittest.main()
