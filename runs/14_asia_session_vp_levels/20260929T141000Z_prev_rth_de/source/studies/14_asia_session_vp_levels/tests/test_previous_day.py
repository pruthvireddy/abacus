"""Signal timing and direction checks for the previous-RTH extension."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.previous_day import session_signals
from src.execution import session_outcomes
from src.previous_day_run import _summary


NS = 60_000_000_000


def row(minute, previous, high, low, close, *, poc=100., vah=104., val=96.,
        reference_complete=True):
    return dict(session_date='2026-01-06', week='2026-01-05', season='EST',
                minute=minute, ts_event=minute * NS, previous_close=previous,
                open=previous, high=high, low=low, close=close,
                rth_poc=poc, rth_vah=vah, rth_val=val,
                reference_complete=reference_complete, reference_contract_clean=True,
                reference_source_degraded=False, source_degraded=False,
                raw_symbol='NQH6', roll_id=1, volatility60=2.)


class PreviousDaySignals(unittest.TestCase):
    def test_first_poc_touches_fade_the_approach_and_enter_next_open(self):
        rows = [row(120, 102, 102, 99.75, 100.5),
                row(121, 100.5, 101, 100, 100.75),
                row(122, 98, 100.25, 98, 99.5),
                row(123, 99.5, 100, 99, 99.75),
                row(124, 102, 102, 99.75, 100.5),
                row(125, 100.5, 101, 100, 100.75)]
        _, signals = session_signals(rows)
        fades = [s for s in signals if s['setup'] == 'D']
        self.assertEqual([(s['direction'], s['minute'], s['entry_ts']) for s in fades],
                         [(1, 120, 121 * NS), (-1, 122, 123 * NS)])
        self.assertTrue(all(s['status'] == 'accepted' for s in fades))

    def test_breakout_requires_later_confirmed_retest(self):
        rows = [row(118, 103.75, 104.5, 103.5, 104.25),
                row(119, 104.25, 105, 104.5, 104.75),
                row(120, 104.75, 105, 103.75, 104.5),
                row(121, 104.5, 105, 104.25, 104.5)]
        ledger, signals = session_signals(rows)
        continuation = [s for s in signals if s['setup'] == 'E']
        self.assertEqual(len(continuation), 1)
        self.assertEqual((continuation[0]['direction'], continuation[0]['origin_minute'],
                          continuation[0]['minute'], continuation[0]['status']),
                         (1, 118, 120, 'accepted'))
        self.assertEqual(sum(x['status'] == 'armed' for x in ledger if x['setup'] == 'E'), 1)

    def test_missing_reference_flags_candidate_without_entry(self):
        rows = [row(120, 102, 102, 99.75, 100.5, reference_complete=False),
                row(121, 100.5, 101, 100, 100.75)]
        _, signals = session_signals(rows)
        self.assertEqual([(s['setup'], s['status']) for s in signals],
                         [('D', 'reference_unavailable')])

    def test_five_ten_twenty_bar_outcomes_use_next_open_and_signed_close(self):
        rows = [row(120, 102, 102, 99.75, 100.5)]
        for minute in range(121, 141):
            candle = row(minute, 100.5, 101.5, 100.25, 101.)
            candle['open'] = 100.5
            rows.append(candle)
        _, signals = session_signals(rows)
        outcomes = {r['horizon']: r for r in session_outcomes(
            rows, [s for s in signals if s['status'] == 'accepted'], horizons=(5, 10, 20))
                    if r['horizon']}
        self.assertEqual(set(outcomes), {5, 10, 20})
        self.assertTrue(all(r['path_status'] == 'complete' for r in outcomes.values()))
        self.assertTrue(all(r['entry'] == 100.5 and r['terminal_points'] == .5
                            and r['mfe_points'] == 1. and r['mae_points'] == .25
                            for r in outcomes.values()))
        summary = _summary([dict(item, split='development') for item in outcomes.values()])
        self.assertEqual(set(summary.horizon), {5, 10, 20})
        self.assertTrue(all(summary.n == 1))
        self.assertTrue(all(summary.avg_close_delta_points == .5))


if __name__ == '__main__':
    unittest.main()
