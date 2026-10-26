"""Reproducible synthetic engine/reference parity; never reads market outcomes.

The independently authored verifier does not import the engine.  This test feeds
both implementations identical synthetic inputs across the declared parameter
settings.  It complements the explicit boundary examples in test_engine.py.
"""
import math
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine import fixture
from src.engine import candidates, simulate
from src.verification import reference_candidates, reference_outcome

SEED = 2602101
SYNTHETIC_SESSIONS = 400
OUTCOMES_PER_SESSION = 16


class ReferenceParityTests(unittest.TestCase):
    def compare_fields(self, actual, expected):
        for field, value in expected.items():
            with self.subTest(field=field):
                found = actual[field]
                if isinstance(value, bool):
                    self.assertIs(found, value)
                elif isinstance(value, (int, float)):
                    self.assertIsNotNone(found)
                    self.assertTrue(math.isclose(found, value, rel_tol=0, abs_tol=1e-8),
                                    f"{field}: {found!r} != {value!r}")
                else:
                    self.assertEqual(found, value)

    def test_randomized_valid_sessions_and_sixteen_variants(self):
        rng = random.Random(SEED)
        checked_outcomes = 0
        for index in range(SYNTHETIC_SESSIONS):
            session = fixture("long" if index % 2 else "short")
            session["plan"]["pivot_lower"] = 100 - rng.choice((0, .25, .5, 1))
            session["plan"]["pivot_upper"] = 100 + rng.choice((0, .25, .5, 1))
            for bar in session["bars5"]:
                opened = 100 + rng.randint(-16, 16) * .25
                closed = opened + rng.randint(-12, 12) * .25
                bar.update(open=opened, close=closed,
                           high=max(opened, closed) + rng.randint(0, 12) * .25,
                           low=min(opened, closed) - rng.randint(0, 12) * .25,
                           ema20=100 + rng.randint(-8, 8) * .25,
                           ema50=100 + rng.randint(-8, 8) * .25,
                           ema20_lag3=100 + rng.randint(-10, 10) * .25,
                           ema50_lag3=100 + rng.randint(-10, 10) * .25,
                           atr14=rng.choice((2, 5, 10, 12.6, 20)))
            level = 100 + rng.randint(-10, 10) * .25
            for bar in session["minutes"]:
                opened = level
                closed = opened + rng.randint(-4, 4) * .25
                bar.update(open=opened, close=closed,
                           high=max(opened, closed) + rng.randint(0, 8) * .25,
                           low=min(opened, closed) - rng.randint(0, 8) * .25)
                level = closed
            for direction in ("long", "short"):
                session["plan"]["targets"][direction] = [
                    dict(lower=90 + ordinal * 10 + rng.randint(-4, 4) * .25,
                         upper=92 + ordinal * 10 + rng.randint(-4, 4) * .25,
                         description="saved", ordinal=ordinal + 1, source_row_id="r" + str(ordinal))
                    for ordinal in range(2)]
            proximity = rng.choice((.05, .10, .15))
            buffer = rng.choice((.5, 1, 1.5))
            actual, _ = candidates(session, proximity, buffer)
            expected = reference_candidates(session, proximity, buffer)
            with self.subTest(session=index, proximity=proximity, stop_buffer=buffer):
                self.assertEqual(len(actual), len(expected))
                for formed, reference in zip(actual, expected):
                    self.compare_fields(formed, reference)
                selected = actual[0] if actual else None
                reference = expected[0] if expected else None
                for entry in ("early", "confirmed"):
                    for mask in "ABCD":
                        for exit_policy in ("fixed_2r", "verne"):
                            slippage = rng.choice((1, 2, 4))
                            with self.subTest(entry=entry, mask=mask, exit_policy=exit_policy, slippage=slippage):
                                outcome = simulate(session, selected, entry, mask, exit_policy, slippage)
                                reference_result = reference_outcome(session, reference, entry, mask, exit_policy, slippage)
                                self.compare_fields(outcome, reference_result)
                                checked_outcomes += 1
        self.assertEqual(checked_outcomes, SYNTHETIC_SESSIONS * OUTCOMES_PER_SESSION)


if __name__ == "__main__":
    unittest.main()
