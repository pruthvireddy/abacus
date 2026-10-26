"""Exercise actual scalar Pine helper bodies; this is not a Pine compiler.

Only scalar assignment, if/else, boolean/arithmetic expressions, na(), and a
final return expression are translated. Pine series history, rollback, plots,
and tables are outside this test's scope and need TradingView verification.
"""

from pathlib import Path
import re
import unittest


PINE_PATH = Path(__file__).resolve().parents[1] / "pine/gc_band_mae_mfe_study_panel.pine"
SOURCE = PINE_PATH.read_text()


def scalar_helper(name):
    lines = SOURCE.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(name + "("))
    signature = lines[start].split("(", 1)[1].rsplit(")", 1)[0]
    arguments = [parameter.strip().split()[-1] for parameter in signature.split(",")]
    body = []
    for line in lines[start + 1 :]:
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
    # Pine returns its last expression, which these helpers leave at base indent.
    if not body[-1].startswith("    ") or body[-1].startswith("        "):
        raise ValueError("Expected a final base-indented scalar return")
    body[-1] = "    return " + body[-1].strip()
    namespace = {"_missing": lambda value: value is None}
    exec("def " + name + "(" + ", ".join(arguments) + "):\n" + "\n".join(body), namespace)
    return namespace[name]


SIZE_PASS = scalar_helper("signalSizePass")
ADVANCE = scalar_helper("advanceEntryModel")


class PineEntryModelsTest(unittest.TestCase):
    def step(self, index, *, state=(None, None), setup=False, close=99.0,
             band=100.0, wait=2, reclaim=True, confirmed=True, contiguous=True):
        return ADVANCE(reclaim, confirmed, contiguous, setup, index, close, band,
                       wait, state[0], state[1])

    def test_size_filter_boundary_and_unavailable_baseline(self):
        self.assertTrue(SIZE_PASS(True, 20.0, 10.0, 2.0))
        self.assertFalse(SIZE_PASS(True, 20.01, 10.0, 2.0))
        self.assertFalse(SIZE_PASS(True, 0.0, 0.0, 2.0))
        self.assertFalse(SIZE_PASS(True, 10.0, None, 2.0))
        self.assertTrue(SIZE_PASS(False, 100.0, None, 2.0))

    def test_immediate_model_preserves_signal_stream(self):
        expected = [False, True, True, False, True]
        actual = [self.step(i, setup=value, reclaim=False)[0]
                  for i, value in enumerate(expected)]
        self.assertEqual(actual, expected)

    def test_setup_cannot_confirm_itself_even_if_wick_reclaimed(self):
        ready, index, level, _ = self.step(10, setup=True, close=101.0)
        self.assertFalse(ready)
        self.assertEqual((index, level), (10, 100.0))
        self.assertTrue(self.step(11, state=(index, level), close=101.0)[0])

    def test_band_is_frozen_and_last_wait_candle_is_inclusive(self):
        state = self.step(10, setup=True)[1:3]
        first = self.step(11, state=state, close=100.0, band=98.0)
        self.assertFalse(first[0])  # Equal original band; above moving band.
        last = self.step(12, state=first[1:3], close=100.01, band=97.0)
        self.assertTrue(last[0])
        self.assertEqual(last[1:3], [None, None])

    def test_expired_setup_does_not_confirm_late(self):
        state = self.step(10, setup=True)[1:3]
        expired = self.step(12, state=state, close=100.0)
        self.assertEqual(expired[:3], [False, None, None])
        self.assertFalse(self.step(13, state=expired[1:3], close=110.0)[0])

    def test_extra_contacts_do_not_replace_or_extend_setup(self):
        state = self.step(10, setup=True)[1:3]
        repeated = self.step(11, state=state, setup=True, band=95.0, close=94.0)
        self.assertEqual(repeated[1:3], [10, 100.0])
        self.assertEqual(self.step(12, state=repeated[1:3], close=96.0)[:3],
                         [False, None, None])

    def test_expiry_candle_can_start_new_setup(self):
        renewed = self.step(12, state=(10, 100.0), setup=True, close=94.0, band=95.0)
        self.assertEqual(renewed[:3], [False, 12, 95.0])
        self.assertTrue(self.step(13, state=renewed[1:3], close=96.0)[0])

    def test_confirmation_does_not_also_start_another_setup(self):
        result = self.step(11, state=(10, 100.0), setup=True, close=101.0, band=102.0)
        self.assertEqual(result[:3], [True, None, None])

    def test_gap_cancels_old_setup_and_can_arm_new_setup(self):
        cancelled = self.step(11, state=(10, 100.0), close=110.0, contiguous=False)
        self.assertEqual(cancelled, [False, None, None, None])
        fresh = self.step(11, state=(10, 100.0), setup=True, close=94.0,
                          band=95.0, contiguous=False)
        self.assertEqual(fresh[:3], [False, 11, 95.0])

    def test_unconfirmed_candle_cannot_advance_state(self):
        result = self.step(11, state=(10, 100.0), close=110.0, confirmed=False)
        self.assertEqual(result, [False, 10, 100.0, 100.0])

    def test_minimum_and_maximum_wait(self):
        for wait in (1, 30):
            with self.subTest(wait=wait):
                self.assertTrue(self.step(10 + wait, state=(10, 100.0),
                                          close=101.0, wait=wait)[0])
                self.assertFalse(self.step(11 + wait, state=(10, 100.0),
                                           close=101.0, wait=wait)[0])

    def test_all_consumers_use_model_confirmations(self):
        # Integration guards: the tested helper must feed the shared acceptance
        # gate, delayed entry, and weekly denominator rather than the raw setup.
        self.assertIn("and closeFilterPass and sizeFilterPass and barstate.isconfirmed", SOURCE)
        self.assertIn("float priorAtr = ta.atr(atrLengthInput)[1]", SOURCE)
        self.assertIn("if entryReadySignal and bar_index - study.lastSignalIndex > cooldownBars", SOURCE)
        self.assertNotIn("if candidateSignal and bar_index - study.lastSignalIndex", SOURCE)
        self.assertIn("study.lastSignalIndex == bar_index - 1 and signalYearInScope[1]", SOURCE)
        self.assertIn("array.push(study.entryPricesArray, open)", SOURCE)
        self.assertIn("if entryReadySignal\n        array.set(weekReadyArray", SOURCE)


if __name__ == "__main__":
    unittest.main()
