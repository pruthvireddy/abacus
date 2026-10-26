"""Causal study-14 signal ledger and next-open path extraction.

Feature snapshots are pre-bar and already contain the unadjusted execution OHLC.
This module never rebuilds a published feature or uses post-bar levels to signal.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math

import numpy as np

from .events import Arm, breakout, touch, retest, selected_hvn_touches, confirmed_hvn, entry_status
from .outcomes import excursion, fixed_path, race, structural

MINUTE_NS = 60_000_000_000
HORIZONS = (5, 15, 30, 60, 120)
SECONDARY_DISTANCES = (2., 4., 8., 12., 20.)


def finite(value):
    return value is not None and math.isfinite(float(value))


def _strict(record, setup):
    common = (record['overnight_complete'] and record['overnight_contract_clean']
              and not record['source_degraded'])
    if setup != 'C':
        return bool(common)
    return bool(common and record['hvn_complete'] and record['hvn_contract_clean']
                and record['reference_complete'] and record['reference_contract_clean']
                and not record['hvn_source_degraded'] and not record['reference_source_degraded'])


def _base(record, setup, direction, level, origin=None, node=None, variant='primary'):
    return {
        'setup': setup, 'variant': variant, 'direction': direction,
        'session_date': record['session_date'], 'year': int(record['session_date'][:4]),
        'week': record['week'], 'season': record['season'],
        'minute': int(record['minute']), 'hour': 18 + int(record['minute']) // 60,
        'signal_ts': int(record['ts_event']), 'level': float(level),
        'on_poc': float(record['on_poc']), 'on_vah': float(record['on_vah']),
        'on_val': float(record['on_val']), 'volatility60': float(record['volatility60']),
        'va_width': float(record['on_vah'] - record['on_val']),
        'raw_symbol': record['raw_symbol'], 'roll_id': int(record['roll_id']),
        'origin_minute': None if origin is None else origin.origin,
        'origin_level': None if origin is None else origin.level,
        'origin_poc': None if origin is None else origin.poc,
        'pre_20_origin': None if origin is None else origin.origin < 120,
        'node_id': None if node is None else node['node_id'],
        'candidate_id': None if node is None else node['candidate_id'],
        'node_lo': None if node is None else node['lo'],
        'node_hi': None if node is None else node['hi'],
        'node_strength': None if node is None else node['strength'],
        'node_rank': None if node is None else node['rank'],
        'node_available_at': None if node is None else node['available_at'],
        'node_match_ambiguous': None if node is None else node['match_ambiguous'],
        'reference': (record['on_vah'] if direction == 1 else record['on_val']) if setup == 'A'
                     else (record['on_poc'] if setup == 'B' else None),
    }


def _ledger_item(record, setup, direction, status, origin=None, node=None, detail=None):
    return {'session_date': record['session_date'], 'year': int(record['session_date'][:4]),
            'minute': int(record['minute']), 'ts_event': int(record['ts_event']),
            'setup': setup, 'direction': direction, 'status': status,
            'origin_minute': None if origin is None else origin.origin,
            'node_id': None if node is None else node['node_id'], 'detail': detail}


def session_signals(records, *, level_mode='developing'):
    """Return every armed/triggered opportunity, plus independently eligible entries.

    records is one futures-session evening sorted by timestamp. Rejection and
    cancellation records are retained. A/B arms can originate from 18:00.
    """
    if level_mode not in ('developing','frozen_breakout'):
        raise ValueError('unknown level mode')
    if not records:
        return [], []
    ledger, signals = [], []
    arms = {'A': None, 'B': None}
    used_nodes = set()
    last_accept = {}
    session = records[0]['session_date']
    for i, r in enumerate(records):
        minute = int(r['minute'])
        previous = r['previous_close']
        new_side = 0
        if finite(previous) and finite(r['on_vah']) and breakout(previous, r['close'], r['on_vah'], 1):
            new_side = 1
        elif finite(previous) and finite(r['on_val']) and breakout(previous, r['close'], r['on_val'], -1):
            new_side = -1
        for setup in ('A', 'B'):
            arm = arms[setup]
            if arm is not None:
                why = arm.availability(minute, session, bool(new_side and new_side != arm.side))
                if why in ('expired', 'opposite_cancelled', 'session_cancelled'):
                    ledger.append(_ledger_item(r, setup, arm.side, why, arm))
                    arms[setup] = arm = None
            if new_side:
                # A fresh price crossing replaces a prior arm of either side.
                if arm is not None:
                    ledger.append(_ledger_item(r, setup, arm.side, 'superseded_breakout', arm))
                level = r['on_vah'] if new_side == 1 else r['on_val']
                arms[setup] = Arm(new_side, minute, session, level, r['on_poc'])
                ledger.append(_ledger_item(r, setup, new_side, 'armed', arms[setup]))
                continue
            if arm is None or minute == arm.origin:
                continue
            if level_mode == 'frozen_breakout':
                level = arm.poc if setup == 'A' else arm.level
            else:
                level = r['on_poc'] if setup == 'A' else (r['on_vah'] if arm.side == 1 else r['on_val'])
            if not finite(previous) or not finite(level):
                continue
            touched = touch(previous, r['high'], r['low'], level, arm.side)
            if not touched:
                continue
            if setup == 'B':
                decision = retest(previous, r['high'], r['low'], r['close'], level, arm.side)
                if decision == 'failed_retest_cancelled':
                    ledger.append(_ledger_item(r, setup, arm.side, decision, arm))
                    arms[setup] = None
                    continue
                if decision == 'unconfirmed':
                    ledger.append(_ledger_item(r, setup, arm.side, 'unconfirmed_retest', arm))
                    # Touch-only sensitivity is still a genuine encounter.
                    variant = 'touch_only'
                else:
                    variant = 'primary'
            else:
                variant = 'primary'
            direction = arm.side
            base = _base(r, setup, direction, level, arm, variant=variant)
            base['rejection_confirmed'] = (direction * (r['close'] - level) > 0) if setup == 'A' else None
            ledger.append(_ledger_item(r, setup, direction, 'triggered', arm, detail=variant))
            if variant == 'primary':
                arms[setup] = None
            signals.append((i, base))
        if finite(previous):
            touched_nodes = selected_hvn_touches(previous, r['high'], r['low'], r['selected'] or [])
            fresh = [n for n in touched_nodes if (n['node_id'], n['side']) not in used_nodes]
            if fresh:
                for node in fresh:
                    used_nodes.add((node['node_id'], node['side']))
                if len(fresh) > 1:
                    for node in fresh:
                        ledger.append(_ledger_item(r, 'C', -node['side'], 'multi_node_ambiguous', node=node))
                elif fresh[0]['match_ambiguous']:
                    ledger.append(_ledger_item(r, 'C', -fresh[0]['side'], 'node_match_ambiguous', node=fresh[0]))
                else:
                    node = fresh[0]
                    base = _base(r, 'C', -node['side'], node['lo'] if node['side'] == 1 else node['hi'], node=node)
                    base['rejection_confirmed'] = confirmed_hvn(node, r['close'])
                    base['post_selected'] = any(x['candidate_id'] == node['candidate_id'] for x in (r['post_selected'] or []))
                    ledger.append(_ledger_item(r, 'C', base['direction'], 'triggered', node=node))
                    signals.append((i, base))
        # Prespecified confirmation subsets share the same causal signal candle.
        # The B touch-only cohort includes confirmed as well as unconfirmed touches.
        new_signals=[x for x in signals if x[0] == i]
        for _, signal in new_signals:
            if signal['setup']=='B' and signal['variant']=='primary':
                signals.append((i,dict(signal,variant='touch_only')))
            elif signal['setup'] in ('A','C') and signal['variant']=='primary' and signal['rejection_confirmed']:
                signals.append((i,dict(signal,variant='rejection_confirmed')))
        # Resolve eligibility after every signal has been detected. In particular,
        # source quality, next-bar gaps and lockouts cannot invent a touch.
        for signal_i, signal in [x for x in signals if x[0] == i]:
            setup, direction = signal['setup'], signal['direction']
            reason = None
            if not 120 <= minute < 359:
                reason = 'outside_signal_window'
            elif not _strict(r, setup):
                reason = 'input_unavailable'
            else:
                next_r = records[i+1] if i+1 < len(records) else None
                reason = entry_status(r['ts_event'], None if next_r is None else next_r['ts_event'],
                                      360 if next_r is None else int(next_r['minute']))
                if reason == 'next_open_eligible':
                    if next_r['raw_symbol'] != r['raw_symbol'] or next_r['roll_id'] != r['roll_id']:
                        reason = 'entry_contract_change'
                    elif next_r['source_degraded']:
                        reason = 'entry_source_degraded'
                    else:
                        reason = None
            if reason is None:
                signal['entry_index'] = i+1
                signal['entry_ts'] = int(records[i+1]['ts_event'])
                signal['entry'] = float(records[i+1]['open'])
                signal['entry_distance_points'] = abs(signal['entry'] - signal['level'])
                signal['near_entry_2_points'] = signal['entry_distance_points'] <= 2
                key = (setup, direction, signal['variant'])
                last = last_accept.get(key)
                if last is not None and minute - last < 15:
                    reason = 'lockout_15m'
                else:
                    last_accept[key] = minute
            signal['status'] = reason or 'accepted'
            if reason is not None and reason != 'lockout_15m': signal['entry_index'] = None
            ledger.append(_ledger_item(r, setup, direction, signal['status'], detail=signal['variant']))
    for setup, arm in arms.items():
        if arm is not None:
            ledger.append(_ledger_item(records[-1], setup, arm.side, 'unreturned_at_midnight', arm))
    # Lockout sensitivities re-use the complete presignal candidate ledger.
    # A baseline-suppressed signal still has its genuine next-open price saved.
    baseline=[x for _,x in signals if x['variant']=='primary' and x['status'] in ('accepted','lockout_15m')]
    for minutes in (0,30):
        accepted={}
        for signal in baseline:
            key=(signal['setup'],signal['direction'])
            prior=accepted.get(key)
            if prior is not None and signal['minute']-prior<minutes:
                continue
            accepted[key]=signal['minute']
            clone=dict(signal,variant=f'lockout_{minutes}',status='accepted')
            signals.append((-1,clone))
    return ledger, [x for _, x in signals]


def session_outcomes(records, signals, horizons=HORIZONS):
    """All fixed horizons, including explicit censoring and failed paths."""
    times = np.asarray([r['ts_event'] for r in records], dtype=np.int64)
    opens = np.asarray([r['open'] for r in records], dtype=float)
    highs = np.asarray([r['high'] for r in records], dtype=float)
    lows = np.asarray([r['low'] for r in records], dtype=float)
    closes = np.asarray([r['close'] for r in records], dtype=float)
    symbols = np.asarray([r['raw_symbol'] for r in records])
    rolls = np.asarray([r['roll_id'] for r in records])
    degraded = np.asarray([r['source_degraded'] for r in records], dtype=bool)
    rows = []
    for signal in signals:
        if signal['status'] != 'accepted':
            continue
        start = signal['entry_index']
        holding_to_midnight=360-int(records[start]['minute'])
        for h in (*horizons,0):
            actual_h=holding_to_midnight if h==0 else h
            path, reason = fixed_path(times, start, int(records[start]['minute']), actual_h)
            if path is not None and (np.any(symbols[path] != signal['raw_symbol'])
                                     or np.any(rolls[path] != signal['roll_id'])):
                path, reason = None, 'path_contract_change'
            if path is not None and np.any(degraded[path]):
                path, reason = None, 'path_source_degraded'
            row = {k: v for k, v in signal.items() if k != 'entry_index'}
            row.update(horizon=h,horizon_label='to_midnight' if h==0 else f'{h}m',
                       holding_minutes=actual_h,path_status=reason)
            if path is not None:
                o, hi, lo, c = opens[path], highs[path], lows[path], closes[path]
                row.update(excursion(o, hi, lo, c, signal['direction'], signal['volatility60'], signal['va_width']))
                row['terminal_positive'] = row['terminal_points'] > 0
                row['signed_path'] = (signal['direction'] * (c-o[0])).tolist()
                row['reference_hit'] = structural(o, hi, lo, signal['direction'], signal['reference'])
                for distance in SECONDARY_DISTANCES:
                    row[f'race_{int(distance)}pt'] = race(o, hi, lo, signal['direction'], distance, distance)
                if h == 30 and finite(signal['volatility60']) and signal['volatility60'] > 0:
                    row['race_tr60'] = race(o, hi, lo, signal['direction'], signal['volatility60'], signal['volatility60'])
                else:
                    row['race_tr60'] = None
            rows.append(row)
    return rows
