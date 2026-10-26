#!/usr/bin/env python3
"""Extend current native exports using older native EMA seeds and OHLC.

Older exports must overlap the current export by at least one bar and differ
only by a constant continuous-contract adjustment. Older files are discovered
as native_SYMBOL_older*.csv, or supplied with repeated --older SYMBOL=PATH.
The resulting reconstructed_SYMBOL.csv files are explicitly analytical
reconstructions, not TradingView-exported indicator signal files.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

import analyze as base

ROOT = Path(__file__).resolve().parent
FIELDS = ("time", "open", "high", "low", "close", "Fast EMA (15m)",
          "Slow EMA (15m)", "News entry side", "News measured side",
          "News event timestamp", "News release components")


def read(path):
    with path.open(newline="") as handle:
        raw = list(csv.DictReader(handle))
    assert raw, f"Empty source {path}"
    fast = "Fast EMA (15m)" if "Fast EMA (15m)" in raw[0] else "Fast EMA"
    slow = "Slow EMA (15m)" if "Slow EMA (15m)" in raw[0] else "Slow EMA"
    rows = {}
    for source in raw:
        t = base.stamp(source["time"])
        assert t not in rows and t % base.BAR == 0
        row = {key: float(source[key]) for key in base.OHLC}
        row.update(time=t,
                   native_fast=float(source[fast]) if source.get(fast) else None,
                   native_slow=float(source[slow]) if source.get(slow) else None,
                   native_signal=int(float(source.get("News measured side") or 0)),
                   source=str(path.resolve()))
        rows[t] = row
    audit = {"path": str(path.resolve()), "sha256": base.digest(path), "bars": len(rows),
             "first_bar_utc": base.iso(min(rows)), "last_bar_utc": base.iso(max(rows))}
    for key, length in (("native_fast", 20), ("native_slow", 50)):
        times = sorted(rows)
        errors = [abs(rows[b][key]-(rows[a][key]+(rows[b]["close"]-rows[a][key])*2/(length+1)))
                  for a,b in zip(times,times[1:]) if rows[a][key] is not None and rows[b][key] is not None]
        assert errors and max(errors)<1e-10, (path, key, max(errors, default=None))
        audit[key+"_recurrence"] = {"pairs": len(errors), "max_abs_error": max(errors)}
    return rows, audit


def reconstruct(symbol, primary_path, older_paths, calendar, output, days):
    merged, primary_audit = read(primary_path)
    latest = max(merged)
    start = latest-days*86400
    native_sources = [dict(merged)]
    audits = [{**primary_audit, "role": "current_price_anchor", "offset_to_current_prices": 0.}]
    for older_path in older_paths:
        older, audit = read(older_path)
        overlap = sorted(set(older)&set(merged))
        assert overlap, f"{symbol}: older source has no overlap for adjustment alignment: {older_path}"
        differences = [merged[t][key]-older[t][key] for t in overlap for key in base.OHLC]
        offset = median(differences)
        max_residual = max(abs(x-offset) for x in differences)
        assert max_residual<1e-10, (symbol, "Nonconstant price overlap", older_path, max_residual)
        for t, row in older.items():
            for key in (*base.OHLC, "native_fast", "native_slow"):
                if row[key] is not None:
                    row[key] += offset
            if t not in merged:
                merged[t] = row
            else:
                # Native older EMA seed can fill the current export's initial
                # hidden warmup. Prices always stay anchored to current export.
                for key in ("native_fast", "native_slow"):
                    if merged[t][key] is None and row[key] is not None:
                        merged[t][key] = row[key]
        native_sources.append(older)
        audits.append({**audit, "role": "older_native_seed_and_prices", "overlap_bars": len(overlap),
                       "offset_to_current_prices": offset, "max_abs_overlap_residual": max_residual})
    times = sorted(merged)
    seed = next(t for t in times if merged[t]["native_fast"] is not None and merged[t]["native_slow"] is not None)
    fast, slow = merged[seed]["native_fast"], merged[seed]["native_slow"]
    reconstructed = {}
    for t in times:
        if t<seed:
            reconstructed[t] = (None,None)
            continue
        if t>seed:
            fast += (merged[t]["close"]-fast)*2/21
            slow += (merged[t]["close"]-slow)*2/51
        reconstructed[t] = (fast,slow)
    # Every native selected observation in the final study must have exactly
    # the same direction under the continuous historical seed. Record numeric
    # EMA differences at those entries, rather than silently accepting them.
    checks, differences = [], []
    for native in native_sources:
        for t,row in native.items():
            if not row["native_signal"] or not start<=t+base.BAR<=latest+base.BAR:
                continue
            fast,slow = reconstructed[t]
            direction = 1 if fast>slow else -1 if fast<slow else 0
            assert direction == row["native_signal"], (symbol, base.iso(t+base.BAR), "Native/reconstructed direction conflict")
            if row["native_fast"] is not None and row["native_slow"] is not None:
                differences += [abs(fast-row["native_fast"]), abs(slow-row["native_slow"])]
            checks.append(t)
    generated = []
    for t in times:
        row = merged[t]
        fast,slow = reconstructed[t]
        event = t+base.BAR
        components = calendar.get(event)
        eligible = start<=event<=latest+base.BAR and components and fast is not None and slow is not None
        side = (1 if fast>slow else -1 if fast<slow else 0) if eligible else 0
        generated.append({"time":t, **{key:row[key] for key in base.OHLC},
                          "Fast EMA (15m)":fast if fast is not None else "",
                          "Slow EMA (15m)":slow if slow is not None else "",
                          "News entry side":side, "News measured side":side,
                          "News event timestamp":event*1000 if side else "",
                          "News release components":len(components) if side else ""})
    path = output/f"reconstructed_{symbol}.csv"
    base.write_csv(path, generated)
    return path, {"symbol":symbol, "sources":audits, "merged_bars":len(times),
                  "study_start_inclusive_utc":base.iso(start), "end_last_bar_utc":base.iso(latest),
                  "continuous_EMA_seed_utc":base.iso(seed),
                  "seed_source":merged[seed]["source"],
                  "seed_fast20":merged[seed]["native_fast"], "seed_slow50":merged[seed]["native_slow"],
                  "native_selected_entry_checks":len(checks),
                  "all_native_selected_directions_match":True,
                  "max_abs_reconstructed_vs_native_EMA_at_selected_entries":max(differences, default=None),
                  "signals":sum(bool(r["News measured side"]) for r in generated),
                  "output":str(path.resolve()), "output_sha256":base.digest(path),
                  "method":"Native older EMA20/50 seed recursively continued through merged OHLC; current prices anchor all constant adjustment offsets. Calendar signals regenerated only inside latest-primary 365-day window."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--older",action="append",default=[],metavar="SYMBOL=PATH")
    parser.add_argument("--output",type=Path,default=ROOT/"extended_year")
    parser.add_argument("--lookback-days",type=int,default=365)
    args = parser.parse_args()
    older = defaultdict(list)
    for value in args.older:
        symbol,path = value.split("=",1)
        older[symbol.upper()].append(Path(path))
    if not args.older:
        older.update({s:sorted(ROOT.glob(f"native_{s}_older*.csv")) for s in base.SYMBOLS})
        older["6E"] = [ROOT.parent/"6e_news_study"/"prices_replay_2025-12-01_native.csv"]
    calendar,_,calendar_audit = base.archive_events(ROOT.parent/"news_ema_move_checks"/"news_ema_calendar_archive.json")
    args.output.mkdir(parents=True,exist_ok=True)
    audits,inputs = [],[]
    for symbol in base.SYMBOLS:
        primary = ROOT/f"native_{symbol}.csv"
        if symbol=="6E" and not primary.exists():
            primary = ROOT.parent/"news_ema_move_checks"/"native_news_ema_move_archive.csv"
        if not primary.exists() or not older[symbol]:
            continue
        path,audit = reconstruct(symbol,primary,older[symbol],calendar,args.output,args.lookback_days)
        audits.append(audit)
        inputs += ["--input",f"{symbol}={path}"]
    assert inputs,"No primary/older pairs available"
    audit_path = args.output/"reconstruction_audit.json"
    audit_path.write_text(json.dumps({"symbols":[r["symbol"] for r in audits],
                                    "calendar_audit":calendar_audit,"reconstructions":audits},indent=2)+"\n")
    subprocess.run([sys.executable,str(ROOT/"analyze.py"),*inputs,"--output",str(args.output),
                    "--lookback-days",str(args.lookback_days)],check=True)
    report_path = args.output/"summary.json"
    report = json.loads(report_path.read_text())
    report["history_reconstruction"] = {"audit_path":str(audit_path.resolve()),
        "audit_sha256":base.digest(audit_path),
        "method":"Analytical reconstruction from native older EMA seeds and adjusted overlapping OHLC; see reconstruction_audit.json. Reconstructed input CSVs are not direct native indicator exports."}
    report_path.write_text(json.dumps(report,indent=2)+"\n")
    text_path = args.output/"report.txt"
    text_path.write_text("Full-year historical reconstruction\n\n"
        "Older native EMA20/50 seeds were continued through merged native OHLC.\n"
        "Current exported prices anchor constant adjustment offsets on overlap.\n"
        "Every native selected entry direction agrees with the reconstruction.\n"
        "See reconstruction_audit.json for source hashes, offsets, and EMA checks.\n\n"+text_path.read_text())


if __name__=="__main__":
    main()
