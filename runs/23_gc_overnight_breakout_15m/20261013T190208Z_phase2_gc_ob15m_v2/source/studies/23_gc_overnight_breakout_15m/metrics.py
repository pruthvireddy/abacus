"""Saved Phase 1 cohort statistics; no alternative-entry calculations."""
from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from zoneinfo import ZoneInfo

import numpy as np

NY = ZoneInfo("America/New_York")
SESSIONS = ("Asia", "London", "New York", "Outside")
SIDES = ("combined", "long", "short")


def instant(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def session_at(value):
    t = instant(value).astimezone(NY)
    minute = t.hour * 60 + t.minute
    if minute >= 1200 or minute < 120:
        return "Asia"
    if minute < 540:
        return "London"
    if 570 <= minute < 960:
        return "New York"
    return "Outside"


def enrich(trade):
    row = dict(trade)
    t = instant(row["entry_time"]).astimezone(NY)
    row.update(year=str(t.year), session=session_at(row["entry_time"]),
               hour=t.hour, weekday=t.strftime("%A"), entry_ny=t.isoformat())
    start = datetime.fromisoformat(row["broker_day"] + "T04:00:00+00:00")
    row["minutes_since_trading_start"] = (instant(row["entry_time"]) - start).total_seconds() / 60
    return row


def wilson(wins, n):
    if not n:
        return None, None
    z = 1.959963984540054
    p = wins / n
    center = (p + z*z/(2*n)) / (1+z*z/n)
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return center-radius, center+radius


def closed_path(trades):
    rows, total, peak, worst = [], 0., 0., 0.
    for t in sorted((x for x in trades if x["status"] == "completed"),
                    key=lambda x: (x["exit_time"], x["trade_id"])):
        total += t["net_dollars"]
        peak = max(peak, total)
        dd = total - peak
        worst = min(worst, dd)
        rows.append({"trade_id": t["trade_id"], "exit_time": t["exit_time"],
                     "entry_year": t["year"], "cumulative_net_dollars": total,
                     "drawdown_dollars": dd})
    return rows, -worst


def block_interval(trades, field, days, reps=10000):
    """Four-week fixed calendar blocks of full day roster, ratio of saved sums/counts.

    Within each cohort, empty and censored days remain in the block calendar;
    only defined observations enter this conditional-trade denominator.
    """
    if not days or not trades:
        return None, None
    first = min(datetime.fromisoformat(d["broker_day"]) for d in days)
    last = max(datetime.fromisoformat(d["broker_day"]) for d in days)
    blocks = (last - first).days // 28 + 1
    sums, counts = np.zeros(blocks), np.zeros(blocks)
    for t in trades:
        if t["status"] != "completed" or t.get(field) is None:
            continue
        i = (datetime.fromisoformat(t["broker_day"]) - first).days // 28
        sums[i] += t[field]
        counts[i] += 1
    if counts.sum() == 0:
        return None, None
    rng = np.random.default_rng(230015)
    samples = []
    for offset in range(0, reps, 500):
        draw = rng.integers(0, blocks, size=(min(500, reps-offset), blocks))
        den = counts[draw].sum(axis=1)
        num = sums[draw].sum(axis=1)
        samples.extend((num[den > 0] / den[den > 0]).tolist())
    if not samples:
        return None, None
    lo, hi = np.quantile(samples, [.025, .975])
    return float(lo), float(hi)


def cohort(trades, days, *, year="all", session="all", side="combined", intervals=True):
    subset = [t for t in trades if (year == "all" or t["year"] == year)
              and (session == "all" or t["session"] == session)
              and (side == "combined" or t["side"].lower() == side)]
    closed = [t for t in subset if t["status"] == "completed"]
    pnl = [t["net_dollars"] for t in closed]
    win = [v for v in pnl if v > 1e-8]
    loss = [v for v in pnl if v < -1e-8]
    zero = [v for v in pnl if abs(v) <= 1e-8]
    rs = [t["net_r"] for t in closed if t.get("net_r") is not None]
    effective = [t["source_style_r"] for t in closed if t.get("source_style_r") is not None]
    lower, upper = wilson(len(win), len(pnl))
    _, dd = closed_path(closed)
    streak = maximum = 0
    for t in sorted(closed, key=lambda x: (x["exit_time"], x["trade_id"])):
        streak = streak+1 if t["net_dollars"] < -1e-8 else 0
        maximum = max(maximum, streak)
    # Day support is independent of actual-entry cohorts; no session/side is
    # invented for a no-trade day. The web labels this distinct calendar anchor.
    roster = [d for d in days if year == "all" or
              str(instant(d["broker_day"]+"T04:00:00+00:00").astimezone(NY).year) == year]
    day_metrics = session == "all" and side == "combined"
    values = {
        "year": year, "session": session, "side": side,
        "accepted_breakouts": len(subset), "executable_fills": len(subset),
        "completed": len(closed), "censored": len(subset)-len(closed),
        "ambiguous": sum(bool(t.get("ambiguous")) for t in subset),
        "wins": len(win), "losses": len(loss), "breakevens": len(zero),
        "win_rate": len(win)/len(pnl) if pnl else None,
        "win_rate_low": lower, "win_rate_high": upper,
        "gross_points": sum(t["raw_price_points"] for t in closed) if closed else None,
        "gross_dollars": sum(t["raw_price_dollars"] for t in closed) if closed else None,
        "net_points": sum(t["net_points"] for t in closed) if closed else None,
        "net_dollars": sum(pnl) if pnl else None,
        "cost_dollars": sum(t["raw_price_dollars"]-t["net_dollars"] for t in closed) if closed else None,
        "net_r": sum(rs) if rs else None, "r_denominator": len(rs),
        "invalid_r": len(closed)-len(rs), "expectancy_r": mean(rs) if rs else None,
        "source_style_net_r": sum(effective) if effective else None,
        "source_style_r_denominator": len(effective),
        "mean_net_dollars": mean(pnl) if pnl else None,
        "median_net_dollars": median(pnl) if pnl else None,
        "average_win_dollars": mean(win) if win else None,
        "average_loss_dollars": mean(loss) if loss else None,
        "win_sum_dollars": sum(win), "loss_sum_dollars": sum(loss),
        "profit_factor": sum(win)/-sum(loss) if loss else None,
        "payoff_ratio": mean(win)/-mean(loss) if win and loss else None,
        "mfe_points": mean(t["mfe_points"] for t in closed) if closed else None,
        "mae_points": mean(t["mae_points"] for t in closed) if closed else None,
        "holding_minutes": mean(t["holding_minutes"] for t in closed) if closed else None,
        "median_holding_minutes": median(t["holding_minutes"] for t in closed) if closed else None,
        "stop_exits": sum(t["exit_reason"] in ("stop", "reset_stop") for t in closed),
        "timed_exits": sum(t["exit_reason"] in ("time", "timed") for t in closed),
        "max_drawdown_dollars": dd if closed else None,
        "max_losing_streak": maximum if closed else None,
        "entry_share": len(subset)/len(trades) if trades else None,
        "distinct_broker_days": len({t["broker_day"] for t in subset}),
        "mean_minutes_since_start": mean(t["minutes_since_trading_start"] for t in subset) if subset else None,
        "eligible_days": sum(bool(d["eligible"]) for d in roster) if day_metrics else None,
        "valid_ranges": sum(bool(d["valid_range"]) for d in roster) if day_metrics else None,
        "no_trade_days": sum(bool(d["no_trade"]) for d in roster) if day_metrics else None,
        "unknown_days": sum(bool(d["unknown_outcome"]) for d in roster) if day_metrics else None,
        "exclusions": sum(not bool(d["eligible"]) for d in roster) if day_metrics else None,
        "quantity_skips": sum(d["quantity_skips"] for d in roster) if day_metrics else None,
        "day_coverage_start": min((d["broker_day"] for d in roster), default=None) if day_metrics else None,
        "day_coverage_end": max((d["broker_day"] for d in roster), default=None) if day_metrics else None,
        "entry_coverage_start": min((t["entry_ny"] for t in subset), default=None),
        "entry_coverage_end": max((t["entry_ny"] for t in subset), default=None),
        "partial_year": year == "2026" if year != "all" else None,
    }
    if intervals:
        values["mean_dollars_low"], values["mean_dollars_high"] = block_interval(subset, "net_dollars", roster)
        values["expectancy_r_low"], values["expectancy_r_high"] = block_interval(subset, "net_r", roster)
    return values


def summarize(trades, days):
    trades = [enrich(t) for t in trades]
    rows = [cohort(trades, days, year=y, session=s, side=d)
            for y in ("all", *(str(x) for x in range(2018, 2027)))
            for s in ("all", *SESSIONS) for d in SIDES]
    timing = []
    for dimension, labels in (("hour", range(24)),
                              ("weekday", ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))):
        for label in labels:
            selected = [t for t in trades if t[dimension] == label]
            for side in SIDES:
                row = cohort(selected, days, side=side, intervals=False)
                row.update(dimension=dimension, bucket=label,
                           entry_share=row["executable_fills"]/len(trades) if trades else None)
                timing.append(row)
    path, _ = closed_path(trades)
    return trades, rows, timing, path


def write_csv(path, rows, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
