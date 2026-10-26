"""Causal previous-session profile signals for the Asia-window extension.

The caller supplies saved pre-bar profile fields.  No current candle is used to
move a level before that candle's signal decision.
"""
from __future__ import annotations

from .events import Arm, breakout, entry_status, retest, touch
from .execution import finite


def _item(record, setup, side, status, origin=None):
    return {
        'session_date': record['session_date'], 'year': int(record['session_date'][:4]),
        'minute': int(record['minute']),
        'ts_event': int(record['ts_event']), 'setup': setup, 'direction': side,
        'status': status, 'origin_minute': None if origin is None else origin.origin,
    }


def _signal(record, setup, side, level, origin=None):
    vah, val, poc = (record[f'rth_{key}'] for key in ('vah', 'val', 'poc'))
    reference = (vah if side == 1 else val) if setup == 'D' else poc
    return {
        'setup': setup, 'variant': 'primary', 'direction': side,
        'session_date': record['session_date'], 'year': int(record['session_date'][:4]),
        'week': record['week'], 'season': record['season'], 'minute': int(record['minute']),
        'signal_ts': int(record['ts_event']), 'level': float(level),
        'origin_minute': None if origin is None else origin.origin,
        'origin_level': None if origin is None else origin.level,
        'raw_symbol': record['raw_symbol'], 'roll_id': int(record['roll_id']),
        'volatility60': float(record['volatility60']),
        'va_width': float(vah - val) if finite(vah) and finite(val) else float('nan'),
        'reference': float(reference) if finite(reference) else float('nan'),
    }


def _reference_ready(record):
    return bool(all(finite(record[f'rth_{part}']) for part in ('vah', 'poc', 'val'))
                and record['reference_complete']
                and record['reference_contract_clean']
                and not record['reference_source_degraded']
                and not record['source_degraded'])


def session_signals(records, *, fade_from_above_long=True):
    """Return D (POC approach fade) and E (VA breakout/retest) ledgers/signals.

    A first in-window POC contact from each side consumes that side for the
    session.  Breakouts can arm from 18:00, but both setups need a 20:00–00:00
    next-open entry.  The alternative fade direction remains parameterized until
    the user's choice is recorded in the new protocol.
    """
    if not records:
        return [], []
    ledger, signals = [], []
    used_fade_sides = set()
    breakout_arm = None
    last_accept = {}
    session = records[0]['session_date']
    for i, record in enumerate(records):
        minute = int(record['minute'])
        previous = record['previous_close']
        poc, vah, val = (record[f'rth_{key}'] for key in ('poc', 'vah', 'val'))
        if finite(previous) and finite(poc) and 120 <= minute < 359:
            approach = (1 if touch(previous, record['high'], record['low'], poc, 1)
                        else -1 if touch(previous, record['high'], record['low'], poc, -1)
                        else 0)
            if approach:
                side = approach if fade_from_above_long else -approach
                if approach in used_fade_sides:
                    ledger.append(_item(record, 'D', side, 'repeat_contact_suppressed'))
                else:
                    used_fade_sides.add(approach)
                    signal = _signal(record, 'D', side, poc)
                    ledger.append(_item(record, 'D', side, 'triggered'))
                    signals.append((i, signal))
        new_side = 0
        if finite(previous) and finite(vah) and breakout(previous, record['close'], vah, 1):
            new_side = 1
        elif finite(previous) and finite(val) and breakout(previous, record['close'], val, -1):
            new_side = -1
        if breakout_arm is not None:
            why = breakout_arm.availability(minute, session, bool(new_side and new_side != breakout_arm.side))
            if why in ('expired', 'opposite_cancelled', 'session_cancelled'):
                ledger.append(_item(record, 'E', breakout_arm.side, why, breakout_arm))
                breakout_arm = None
        if new_side:
            if breakout_arm is not None:
                ledger.append(_item(record, 'E', breakout_arm.side, 'superseded_breakout', breakout_arm))
            breakout_arm = Arm(new_side, minute, session, vah if new_side == 1 else val, poc)
            ledger.append(_item(record, 'E', new_side, 'armed', breakout_arm))
        elif breakout_arm is not None and minute > breakout_arm.origin:
            side = breakout_arm.side
            level = vah if side == 1 else val
            if finite(previous) and finite(level):
                decision = retest(previous, record['high'], record['low'], record['close'], level, side)
                if decision == 'failed_retest_cancelled':
                    ledger.append(_item(record, 'E', side, decision, breakout_arm))
                    breakout_arm = None
                elif decision == 'confirmed':
                    signal = _signal(record, 'E', side, level, breakout_arm)
                    ledger.append(_item(record, 'E', side, 'triggered', breakout_arm))
                    signals.append((i, signal))
                    breakout_arm = None
                elif decision == 'unconfirmed':
                    ledger.append(_item(record, 'E', side, 'unconfirmed_retest', breakout_arm))
        for signal_i, signal in [x for x in signals if x[0] == i]:
            reason = None
            if not 120 <= minute < 359:
                reason = 'outside_signal_window'
            elif not _reference_ready(record):
                reason = 'reference_unavailable'
            else:
                next_record = records[i + 1] if i + 1 < len(records) else None
                reason = entry_status(record['ts_event'],
                                      None if next_record is None else next_record['ts_event'],
                                      360 if next_record is None else int(next_record['minute']))
                if reason == 'next_open_eligible':
                    if next_record['raw_symbol'] != record['raw_symbol'] or next_record['roll_id'] != record['roll_id']:
                        reason = 'entry_contract_change'
                    elif next_record['source_degraded']:
                        reason = 'entry_source_degraded'
                    else:
                        reason = None
            if reason is None:
                signal['entry_index'] = i + 1
                signal['entry_ts'] = int(records[i + 1]['ts_event'])
                signal['entry'] = float(records[i + 1]['open'])
                signal['entry_distance_points'] = abs(signal['entry'] - signal['level'])
                key = (signal['setup'], signal['direction'])
                prior = last_accept.get(key)
                if prior is not None and minute - prior < 15:
                    reason = 'lockout_15m'
                else:
                    last_accept[key] = minute
            signal['status'] = reason or 'accepted'
            ledger.append(_item(record, signal['setup'], signal['direction'], signal['status']))
    if breakout_arm is not None:
        ledger.append(_item(records[-1], 'E', breakout_arm.side, 'unreturned_at_midnight', breakout_arm))
    return ledger, [signal for _, signal in signals]
