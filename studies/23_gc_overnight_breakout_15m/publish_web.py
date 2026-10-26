"""Prepare Phase 1 publication from explicit saved evidence, without an engine import.

Run only after numerical tables have been saved. This producer projects cells,
draws their presentation geometry and authors labeled illustrations. It neither
calculates a backtest nor recomputes statistics. Existing outputs are refused.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

STUDY = "23_gc_overnight_breakout_15m"
VERSION = "study23.phase1-publication/v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SESSIONS = ("Asia", "London", "New York", "Outside")
COLORS = ("#246b61", "#6952a3", "#aa6040", "#666b78")
TEXT_COLUMNS = {"year", "session", "side", "scenario", "dimension", "broker_day", "trade_id", "status", "exit_reason", "contract", "entry_time", "exit_time", "entry_ny", "day_coverage_start", "day_coverage_end", "entry_coverage_start", "entry_coverage_end"}
INTEGER_COLUMNS = {"accepted_breakouts", "executable_fills", "completed", "censored", "ambiguous", "wins", "losses", "breakevens", "r_denominator", "invalid_r", "source_style_r_denominator", "stop_exits", "timed_exits", "max_losing_streak", "distinct_broker_days", "eligible_days", "valid_ranges", "no_trade_days", "unknown_days", "exclusions", "quantity_skips", "entry_year"}
LABELS = {
    "year": ("Entry year", None, 0), "session": ("Entry session", None, 0), "side": ("Side", None, 0),
    "accepted_breakouts": ("Accepted breakouts", "trades", 0), "executable_fills": ("Executable fills", "trades", 0),
    "completed": ("Completed", "trades", 0), "censored": ("Censored / open", "trades", 0), "ambiguous": ("Ambiguous fills", "trades", 0),
    "wins": ("Net wins", "trades", 0), "losses": ("Net losses", "trades", 0), "breakevens": ("Net breakevens", "trades", 0),
    "win_rate": ("Net win rate", "%", 1), "win_rate_low": ("Win rate 95% lower", "%", 1), "win_rate_high": ("Win rate 95% upper", "%", 1),
    "gross_points": ("Raw-price P&L", "points", 2), "gross_dollars": ("Raw-price P&L", "USD", 2),
    "net_points": ("Net P&L", "points", 2), "net_dollars": ("Net P&L", "USD", 2), "cost_dollars": ("Slip + fees", "USD", 2),
    "net_r": ("Net study R", "R", 3), "r_denominator": ("Valid study R", "trades", 0), "invalid_r": ("Undefined study R", "trades", 0),
    "expectancy_r": ("Mean net study R", "R / trade", 3), "source_style_net_r": ("Source-style net R", "R", 3),
    "source_style_r_denominator": ("Valid source-style R", "trades", 0),
    "mean_net_dollars": ("Mean net trade", "USD / trade", 2), "median_net_dollars": ("Median net trade", "USD / trade", 2),
    "average_win_dollars": ("Average net win", "USD / win", 2), "average_loss_dollars": ("Average net loss", "USD / loss", 2),
    "win_sum_dollars": ("Net winning sum", "USD", 2), "loss_sum_dollars": ("Net losing sum", "USD", 2),
    "profit_factor": ("Profit factor", "ratio", 3), "payoff_ratio": ("Payoff ratio", "ratio", 3),
    "mfe_points": ("Mean trade MFE", "points", 2), "mae_points": ("Mean trade MAE", "points", 2),
    "holding_minutes": ("Mean holding time", "minutes", 1), "median_holding_minutes": ("Median holding time", "minutes", 1),
    "stop_exits": ("Stop exits", "trades", 0), "timed_exits": ("Timed exits", "trades", 0),
    "max_drawdown_dollars": ("Closed-P&L drawdown", "USD", 2), "max_losing_streak": ("Maximum losing streak", "trades", 0),
    "entry_share": ("Share of all entries", "%", 1), "distinct_broker_days": ("Distinct broker days", "days", 0),
    "mean_minutes_since_start": ("Mean time from 07:00 broker", "minutes", 1),
    "eligible_days": ("Eligible days", "days", 0), "valid_ranges": ("Valid complete ranges", "days", 0),
    "no_trade_days": ("Known no-trade days", "days", 0), "unknown_days": ("Unknown days", "days", 0),
    "exclusions": ("Excluded calendar days", "days", 0), "quantity_skips": ("Quantity skips", "sides", 0),
    "day_coverage_start": ("Day-roster start", None, 0), "day_coverage_end": ("Day-roster end", None, 0),
    "entry_coverage_start": ("First entry (New York)", None, 0), "entry_coverage_end": ("Last entry (New York)", None, 0),
    "partial_year": ("Partial year", None, 0), "mean_dollars_low": ("Mean trade 95% lower", "USD / trade", 2),
    "mean_dollars_high": ("Mean trade 95% upper", "USD / trade", 2), "expectancy_r_low": ("Mean R 95% lower", "R / trade", 3),
    "expectancy_r_high": ("Mean R 95% upper", "R / trade", 3), "dimension": ("Timing dimension", None, 0),
    "bucket": ("New York hour / weekday", None, 0), "scenario": ("Execution scenario", None, 0),
    "dd_dollars": ("Full-history closed drawdown", "USD", 2),
    "completed_fill_days": ("Completed-fill days", "days", 0),
    "censored_fill_days": ("Censored-fill days", "days", 0),
    "known_no_trade_days": ("Known no-trade days", "days", 0),
    "unobserved_first_fill_days": ("Unobserved first-fill days", "days", 0),
    "classification_total": ("Disposition total", "days", 0),
    "excluded_calendar_days": ("Excluded calendar days", "days", 0),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def cell(column, value):
    if value == "":
        return None
    if column in TEXT_COLUMNS:
        return value
    if value in {"True", "False", "true", "false"}:
        return value.lower() == "true"
    if column == "partial_year":
        if value not in {"True", "False", "true", "false"}:
            raise ValueError("Invalid saved boolean")
        return value.lower() == "true"
    if column == "bucket" and not value.isdecimal():
        return value
    if column in INTEGER_COLUMNS or column == "bucket":
        number = int(value)
    else:
        try:
            number = float(value)
        except ValueError:
            return value
    if isinstance(number, float) and not math.isfinite(number):
        raise ValueError("Nonfinite saved result")
    return number


class Evidence:
    def __init__(self, stage):
        self.stage = stage
        self.sources, self.bindings, self.figures, self.downloads, self.prose_claims = {}, [], [], [], []

    def read(self, artifact):
        path = self.stage / artifact
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Expected saved regular file: {artifact}")
        with path.open(newline="") as stream:
            raw = list(csv.DictReader(stream))
        self.sources[artifact] = sha(path)
        return [{key: cell(key, value) for key, value in row.items()} for row in raw]

    def binding(self, artifact, source_row, column, section, *, row_index=None, metric_index=None, value=None):
        item = {"section": section, "source_artifact": artifact, "source_row": source_row,
                "source_column": column, "value_type": "null" if value is None else "boolean" if isinstance(value, bool) else "number" if isinstance(value, (float, int)) else "string"}
        if row_index is not None:
            item.update(row_index=row_index, key=column)
        if metric_index is not None:
            item["metric_index"] = metric_index
        self.bindings.append(item)

    def table(self, sid, title, artifact, rows, fields, *, selected=None, filters=True, notes=None, description=None):
        selected = list(range(len(rows))) if selected is None else list(selected)
        if len(fields) > 12:
            raise ValueError("Report tables admit at most twelve columns")
        output = [{key: rows[index][key] for key in fields} for index in selected]
        for row_index, source_row in enumerate(selected):
            for key in fields:
                self.binding(artifact, source_row, key, sid, row_index=row_index, value=rows[source_row][key])
        section = {"id": sid, "kind": "table", "title": title, "columns": [column_spec(key) for key in fields], "rows": output,
                   "description": description or "Exact saved evidence rows; controls select existing cohorts without pooling or recalculating results.",
                   "referenceIds": [reference_id(artifact)]}
        if notes:
            section["notes"] = notes
        if filters:
            section["rowFilters"] = [{"key": "year", "label": "Year", "defaultValue": "all"},
                                     {"key": "session", "label": "Entry session", "defaultValue": "all"},
                                     {"key": "side", "label": "Side", "defaultValue": "combined"}]
        return section


def reference_id(artifact):
    return Path(artifact).stem.replace("_", "-").replace(".", "-")


def column_spec(key):
    label, unit, precision = LABELS.get(key, (key.replace("_", " ").capitalize(), None, 2))
    result = {"key": key, "label": label}
    if unit:
        result.update(format="percent" if unit == "%" else "number", precision=precision)
        if unit != "%":
            result["unit"] = unit
    return result


class SVG:
    def __init__(self, width, height, title, subtitle=""):
        self.width, self.height = width, height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#fff"/>']
        self.text(40, 40, title, size=24, weight="bold")
        self.text(40, 68, subtitle, size=14, color="#545963")

    def text(self, x, y, text, size=14, color="#28323b", anchor="start", weight="normal"):
        self.parts.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(text))}</text>')

    def line(self, x1, y1, x2, y2, color="#b9bec5", width=1, dash=None):
        dashed = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{width}"{dashed}/>')

    def rect(self, x, y, width, height, fill, stroke=None):
        border = f' stroke="{stroke}"' if stroke else ""
        self.parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(0,width):.2f}" height="{max(0,height):.2f}" fill="{fill}"{border}/>')

    def path(self, points, color="#246b61", width=2):
        if points:
            self.parts.append(f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="{width}"/>')

    def marker(self, x, y, direction=None, color="#246b61"):
        if direction:
            dy=10 if direction=="up" else -10
            self.parts.append(f'<polygon points="{x:.2f},{y:.2f} {x-6:.2f},{y+dy:.2f} {x+6:.2f},{y+dy:.2f}" fill="{color}"/>')
        else:
            self.parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}"/>')

    def save(self, path):
        Path(path).write_text("\n".join([*self.parts, "</svg>"]) + "\n")


def money(value):
    return "Unavailable" if value is None else f"${value:,.0f}"


def scale(values, top, bottom):
    finite = [v for v in values if v is not None]
    low, high = min([0, *finite]), max([0, *finite])
    span = high - low or 1
    low, high = low - span * .08, high + span * .08
    return lambda value: bottom - (value - low) / (high - low) * (bottom - top), low, high


def grid(svg, yscale, low, high, left, right, top, bottom, unit="USD"):
    for i in range(5):
        value = low + (high - low) * i / 4
        y = yscale(value)
        svg.line(left, y, right, y, "#e6e8eb")
        svg.text(left - 12, y + 5, f"{value:,.0f}", anchor="end", size=12)
    svg.line(left, yscale(0), right, yscale(0), "#9da4ad", width=1.5)
    svg.text(left, top - 12, unit, size=12)


def bar_chart(path, title, labels, values, subtitle, ylabel="USD", colors=None):
    svg = SVG(1200, 620, title, subtitle)
    left, right, top, bottom = 110, 1160, 135, 525
    ys, low, high = scale(values, top, bottom)
    grid(svg, ys, low, high, left, right, top, bottom, ylabel)
    gap = (right-left) / max(len(labels), 1)
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + gap * (i + .5)
        color = (colors or COLORS)[i % len(colors or COLORS)]
        if value is not None:
            svg.rect(x-gap*.3, min(ys(0), ys(value)), gap*.6, max(abs(ys(value)-ys(0)), 1), color)
            svg.text(x, ys(value) - 10 if value >= 0 else ys(value) + 22, money(value) if ylabel == "USD" else str(int(value)), anchor="middle", size=12)
        else:
            svg.text(x, ys(0)-12, "Unavailable", anchor="middle", size=11)
        svg.text(x, bottom+25, label, anchor="middle", size=11 if len(labels)>12 else 13)
    svg.text(40, 595, "Saved aggregate evidence; labels and signs distinguish cohorts in addition to color.", size=13)
    svg.save(path)


def equity_chart(path, rows):
    svg = SVG(1200, 850, "Cumulative net P&L and closed-trade drawdown", "One GC contract; $2.50 / side + one adverse tick / fill; closed trades only")
    left, right = 110, 1160
    times = [datetime.fromisoformat(r["exit_time"].replace("Z", "+00:00")).timestamp() for r in rows]
    first, last = min(times, default=0), max(times, default=1)
    xs = lambda t: left + (t-first)/(last-first or 1)*(right-left)
    for top, bottom, field, color, name in [(130,420,"cumulative_net_dollars",COLORS[0],"Cumulative net P&L"),(515,750,"drawdown_dollars",COLORS[2],"Drawdown below prior closed-P&L peak")]:
        ys, low, high = scale([r[field] for r in rows], top, bottom)
        grid(svg, ys, low, high, left, right, top, bottom)
        svg.text(left, top-35, name, size=18, weight="bold")
        svg.path([(xs(t),ys(r[field])) for t,r in zip(times, rows)], color, 2)
        for i in range(5):
            t = first + (last-first)*i/4
            svg.text(xs(t), bottom+25, datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m"), anchor="middle", size=12)
    svg.text(40, 824, "Full-history path ordered by exit time. Annual drawdown is calculated on each entry-year cohort separately.", size=13)
    svg.save(path)


def heatmap(path, rows):
    svg = SVG(1200, 790, "Year × actual-entry-session net P&L", "USD, one GC contract; $2.50 / side + one adverse tick / fill; whole result assigned to entry cohort")
    lookup = {(r["year"],r["session"]):r for r in rows if r["side"]=="combined"}
    for j,label in enumerate(SESSIONS):
        svg.text(300+j*205, 117, label, anchor="middle", size=17, weight="bold")
    for i,year in enumerate(map(str,range(2018,2027))):
        partial = any(r["year"]==year and r["partial_year"] for r in rows)
        svg.text(90, 162+i*62, year+(" *" if partial else ""), size=16)
        for j,session in enumerate(SESSIONS):
            value = lookup[(year,session)]["net_dollars"]
            fill = "#eeeeef" if value is None else "#dcf0e9" if value>=0 else "#f6e2d7"
            svg.rect(200+j*205, 130+i*62, 194, 51, fill)
            svg.text(297+j*205, 160+i*62, "— / zero support" if value is None else money(value), anchor="middle", size=14)
    svg.text(40, 740, "* Partial covered year. Positive/negative dollar labels distinguish signs; unavailable remains unavailable.", size=13)
    svg.save(path)


def illustrative_guide(path):
    svg = SVG(1400, 760, "How the Phase 1 breakout is simulated", "Illustrative authored geometry, not observed market data; broker clock is fixed UTC+3")
    for offset, side in [(0,"Long"),(680,"Short")]:
        left, right, top, bottom = 75+offset, 675+offset, 175, 515
        p=lambda v: bottom-(v-968)/82*(bottom-top)
        x=lambda v:left+v*(right-left)/13
        high, low = 1020, 980
        svg.text(left, 120, f"{side}: {'survives, resets, then timed exit' if side=='Long' else 'entry-candle stop precedes any reset'}", size=17, weight="bold")
        svg.rect(x(0),p(high),x(6.5)-x(0),p(low)-p(high),"#ece7f8",stroke="#6952a3")
        for value,label,dash in [(high,"Range high",None),(1000,"Midpoint: visual only","3 4"),(low,"Range low",None)]:
            svg.line(left,p(value),right,p(value),"#6952a3",dash=dash)
            svg.text(left+8,p(value)-8,label,size=12,color="#6952a3")
        svg.line(x(6.5),top,x(6.5),bottom,"#444b55",dash="5 4")
        svg.text(x(6.5),bottom+30,"07:00",anchor="middle",size=13,weight="bold")
        if side=="Long":
            range_points=[(0,999),(2,1017),(4,983),(6,1014),(6.5,1014)]
            points=[(7,1024),(8,1030),(9,1025),(10,1038),(12,1032),(13,1040)]
            initial, reset = 1009.8, 1013.8
            svg.path([(x(t),p(v)) for t,v in range_points],"#246b61",2.3)
            svg.line(x(6.5),p(1014),x(7),p(1024),"#777d86",dash="2 5")
            svg.text(x(7)+10,p(1024)-18,"Opening-gap fill",size=12,color="#246b61")
            svg.marker(x(7),p(1024),"up")
            svg.line(x(6.5),p(initial),x(8),p(initial),"#aa6040",width=2,dash="8 4")
            svg.line(x(8),p(reset),right,p(reset),"#aa6040",width=2,dash="2 3")
            svg.text(x(9),p(reset)-10,"Delayed reset: 1013.8",size=12,color="#aa6040")
            svg.text(x(6.5)-5,p(initial)+22,"Initial: 1009.8",anchor="end",size=12,color="#aa6040")
            svg.marker(x(13),p(1040),color="#444b55")
            svg.text(x(13)-8,p(1040)-20,"Timed exit",anchor="end",size=12)
            svg.text(left,590,"Only a surviving 07:00–07:15 candle resets the stop.",size=14)
            svg.text(left,615,"19:45 candle close queues market exit; normal fill at 20:00 open.",size=13)
        else:
            points=[(0,999),(2,1017),(4,983),(6,1002),(6.5,1002),(7,980),(7.3,974),(7.8,989.8)]
            initial = 989.8
            svg.line(x(6.5),p(initial),x(8),p(initial),"#aa6040",width=2,dash="8 4")
            svg.marker(x(7),p(980),"down")
            svg.text(x(7)-8,p(980)+30,"Boundary-touch fill",anchor="end",size=12,color="#246b61")
            svg.marker(x(7.8),p(initial),color="#aa6040")
            svg.text(x(8)+4,p(initial)+5,"Initial stop exit: 989.8",size=12,color="#aa6040")
            svg.text(left,590,"An entry-candle loss cannot be rescued by a later reset.",size=14)
            svg.text(left,615,"First fill cancels the other order; this broker day is consumed.",size=13)
        svg.path([(x(t),p(v)) for t,v in points],"#246b61",2.3)
        svg.text(left,550,"00:00",size=12)
        svg.text(right,550,"20:00",anchor="end",size=12)
        svg.text(left,650,"07:00: range available and standing stop orders become active.",size=13)
        svg.text(left,675,"07:15: indicator marker known; it cannot confer an earlier live fill.",size=13)
    svg.text(40,725,"Authored price units. Dashed brown = initial stop; dotted brown = reset. Gray dots = explicit opening gap. Midpoint never traded.",size=14)
    svg.save(path)


def empirical_examples(path, bars, selections):
    svg = SVG(1400, 1120, "Observed examples chosen before visual inspection", "Earliest chronological completed net win and net loss per side; pinned same-contract one-minute bars")
    for panel, selected in enumerate(selections):
        trade = selected["trade"]
        observed = [r for r in bars if r["trade_id"] == trade["trade_id"]]
        left, right = 85+(panel%2)*690, 685+(panel%2)*690
        top, bottom = 180+(panel//2)*450, 450+(panel//2)*450
        svg.text(left, top-75, f'{selected["side"].capitalize()} · first net {selected["outcome"]} · {trade["broker_day"]}', size=18, weight="bold")
        svg.text(left, top-48, trade["contract"], size=13)
        times = [datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")).timestamp() for r in observed]
        start, end = min(times), max(times)
        xs = lambda t: left+(t-start)/(end-start or 1)*(right-left)
        stops = [trade["initial_stop"], trade["reset_stop"]]
        values = [r[k] for r in observed for k in ("high","low")]+[v for v in stops if v is not None]
        low, high = min(values), max(values)
        padding = (high-low or 1)*.08
        low, high = low-padding, high+padding
        ys = lambda p: bottom-(p-low)/(high-low)*(bottom-top)
        for i in range(4):
            value = low+(high-low)*i/3
            svg.line(left,ys(value),right,ys(value),"#e7e9ec")
            svg.text(left-8,ys(value)+4,f"{value:.1f}",anchor="end",size=11)
        active = datetime.fromisoformat(trade["order_active_at"].replace("Z", "+00:00")).timestamp()
        overnight = [r for r,t in zip(observed,times) if t<active]
        range_high = max(r["high"] for r in overnight)
        range_low = min(r["low"] for r in overnight)
        svg.rect(left,ys(range_high),xs(active)-left,ys(range_low)-ys(range_high),"#eee9f8")
        for price,dash in [(range_high,None),(range_low,None),((range_high+range_low)/2,"3 4")]:
            svg.line(left,ys(price),right,ys(price),"#6952a3",dash=dash)
        # Wicks preserve the observed minute extrema; the close trace makes
        # densely sampled long days readable without changing any saved bar.
        for row,t in zip(observed,times):
            svg.line(xs(t),ys(row["low"]),xs(t),ys(row["high"]),"#bcc9c6",width=.6)
        svg.path([(xs(t),ys(r["close"])) for t,r in zip(times,observed)],"#246b61",1.3)
        entry = datetime.fromisoformat(trade["entry_time"].replace("Z", "+00:00")).timestamp()
        exit_time = datetime.fromisoformat(trade["exit_time"].replace("Z", "+00:00")).timestamp()
        svg.line(xs(entry),top,xs(entry),bottom,"#246b61",dash="5 4")
        svg.text(xs(entry),top-15,"Fill ▼" if trade["side"]=="short" else "Fill ▲",anchor="middle",size=12,color="#246b61")
        svg.line(xs(exit_time),top,xs(exit_time),bottom,"#444b55",dash="2 4")
        svg.text(min(xs(exit_time),right-30),top-15,"Exit ●",anchor="middle",size=12)
        reset = trade["reset_stop_active_at"]
        reset_time = datetime.fromisoformat(reset.replace("Z", "+00:00")).timestamp() if reset else exit_time
        svg.line(xs(entry),ys(trade["initial_stop"]),xs(reset_time),ys(trade["initial_stop"]),"#aa6040",width=2,dash="8 4")
        if trade["reset_stop"] is not None:
            svg.line(xs(reset_time),ys(trade["reset_stop"]),xs(exit_time),ys(trade["reset_stop"]),"#aa6040",width=2,dash="2 3")
        for step in range(5):
            instant=start+(end-start)*step/4
            svg.text(xs(instant),bottom+25,datetime.fromtimestamp(instant,timezone.utc).strftime("%H:%M"),anchor="middle",size=11)
        svg.text(left,bottom+55,"UTC time; intraminute fill is an estimate with retained minute bounds.",size=12)
        svg.text(left,bottom+79,"Violet: range + visual midpoint; brown dashed/dotted: initial/reset stop.",size=12)
    svg.text(40,1085,"Examples are explanatory, not representative samples. Aggregate evidence and censored trades remain in the report.",size=14)
    svg.save(path)


def text(sid, title, body, references=None):
    return {"id": sid, "kind": "text", "title": title, "body": body, **({"referenceIds": references} if references else {})}


def create_publication(stage, run_id, publication_id, published_at, package_root):
    stage = stage.resolve()
    if not stage.is_relative_to(ROOT / "work" / STUDY) or stage.name != run_id:
        raise ValueError("Publication output must use this study's explicit execution stage")
    for name in ("publication.json", "source-map.json", "publication-generation.json"):
        if (stage/name).exists():
            raise FileExistsError(f"Refusing existing presentation output: {name}")
    snapshot=stage/"source-publication"
    snapshot.mkdir(exist_ok=False)
    producer_records=[]
    for source in (Path(__file__).resolve(),HERE/"rasterize_figures.mjs"):
        target=snapshot/source.name
        shutil.copyfile(source,target)
        producer_records.append({"path":str(target.relative_to(stage)),"sha256":sha(target)})
    ev = Evidence(stage)
    cohorts = ev.read("tables/cohorts.csv")
    timing = ev.read("tables/timing.csv")
    equity = ev.read("tables/equity.csv")
    scenarios = ev.read("tables/scenarios.csv")
    trades = ev.read("tables/primary-trades.csv")
    bars = ev.read("tables/selected-example-bars.csv")
    disposition = ev.read("tables/day-disposition.csv")
    selections = json.loads((stage/"example-selection.json").read_text())
    ev.sources["example-selection.json"] = sha(stage/"example-selection.json")
    frozen = json.loads((stage/"config.json").read_text())
    lock = json.loads((stage/"inputs.lock.json").read_text())
    audit = json.loads((stage/"input-audit/input-summary.json").read_text())
    alias=stage/"input-summary.json"
    if alias.exists():
        if sha(alias)!=sha(stage/"input-audit/input-summary.json"):
            raise ValueError("Existing selected input-summary alias differs")
    else:
        shutil.copyfile(stage/"input-audit/input-summary.json",alias)
    for artifact in ("config.json", "inputs.lock.json", "protocol.md", "input-audit/input-summary.json"):
        ev.sources[artifact] = sha(stage/artifact)
    ev.sources["input-summary.json"] = sha(alias)
    overall_index = next(i for i,r in enumerate(cohorts) if (r["year"],r["session"],r["side"])==("all","all","combined"))
    overall = cohorts[overall_index]
    annual_indices = [i for i,r in enumerate(cohorts) if r["year"]!="all" and r["session"]=="all" and r["side"]=="combined"]
    annual = [cohorts[i] for i in annual_indices]
    sections = []
    claims = []
    finding = (f'The fixed standardized baseline completed {overall["completed"]:,} trades and saved net P&L of '
               f'${overall["net_dollars"]:,.0f} under the assumed costs. Net winners were {overall["wins"]:,} '
               f'of {overall["completed"]:,} completed trades ({overall["win_rate"]*100:.1f}%). '
               f'{overall["censored"]:,} accepted fills have censored or open outcomes and are excluded from closed-P&L statistics.')
    headline_sources=[]
    for key in ("completed","net_dollars","wins","win_rate","censored"):
        headline_sources.append({"source_artifact":"tables/cohorts.csv","source_row":overall_index,"source_column":key,"display":{"style":"percent" if key=="win_rate" else "dollars" if key=="net_dollars" else "number","precision":1 if key=="win_rate" else 0,"grouping":True}})
    claims.append({"id":"overall-headline", "target":{"section":"overview","field":"body"}, "text":finding,
                   "conditions":[{"source_artifact":"tables/cohorts.csv","source_row":overall_index,"source_column":"completed","operator":"gt","value":0}], "sources":headline_sources})
    years_losing = [r["year"] for r in annual if r["net_dollars"] is not None and r["net_dollars"]<0]
    annual_finding = "Negative annual net P&L occurs in "+", ".join(years_losing)+". Positive full-history P&L does not imply consistent annual performance or attainable source-account returns. Read the recent partial-year result alongside its sample size and limited covered dates; the annual rows show concentration without establishing an independent forecast."
    claims.append({"id":"negative-years","target":{"section":"annual","field":"body"},"text":annual_finding,"rule":"negative_annual_years",
                   "conditions":[{"source_artifact":"tables/cohorts.csv","source_row":overall_index,"source_column":"net_dollars","operator":"gt","value":0},*[{"source_artifact":"tables/cohorts.csv","source_row":i,"source_column":"net_dollars","operator":"lt","value":0} for i in annual_indices if cohorts[i]["year"] in years_losing]],
                   "sources":[{"source_artifact":"tables/cohorts.csv","source_row":i,"source_column":"net_dollars"} for i in annual_indices]})
    sections.append(text("overview","Overview",finding+"\n\nThe overnight range is built in fixed UTC+3 from 00:00 inclusive to 07:00 exclusive. Two boundary-touch stop orders become active after the final 06:45–07:00 signal candle closes. First fill cancels the opposite side and consumes the broker day. The primary result uses one executable GC contract; it is descriptive historical evidence under an authored fill model, with important input-quality limits.",["cohorts","config","inputs-lock"]))
    figure_specs = []
    figure_dir = stage/"figures"
    figure_dir.mkdir(exist_ok=True)
    def figure(sid,title,name,alt,caption,artifact=None,source_rows=None,source_columns=None,draw=None,extra_sources=None):
        svgpath=figure_dir/(name+".svg")
        pngpath=figure_dir/(name+".png")
        if svgpath.exists() or pngpath.exists():
            raise FileExistsError("Existing figure overwrite refused")
        draw(svgpath)
        figure_specs.append({"svg":str(svgpath),"png":str(pngpath)})
        record={"section":sid,"path":f"figures/{name}.png","kind":"saved-values" if artifact and artifact!="protocol.md" else "illustrative",
                "source_artifact":artifact,"sha256":ev.sources.get(artifact),"source_rows":source_rows or [],"source_columns":source_columns or []}
        record["source_sha256"] = ev.sources.get(artifact)
        source_lookup={"tables/cohorts.csv":cohorts,"tables/timing.csv":timing,"tables/equity.csv":equity,"tables/selected-example-bars.csv":bars}
        record["plotted_values"]=[{"source_row":i,"values":{key:source_lookup[artifact][i][key] for key in source_columns}} for i in source_rows or []] if artifact else []
        if extra_sources:
            record["extra_sources"]=extra_sources
        ev.figures.append(record)
        section={"id":sid,"kind":"figure","title":title,"path":f"figures/{name}.png","alt":alt,"caption":caption}
        if artifact:
            section["referenceIds"]=[reference_id(artifact)]
        sections.append(section)
    figure("guide","Illustrative entry and exit guide","illustrative-guide","Two authored panels show long boundary breakout, surviving-candle stop reset and timed exit; short entry-candle stop uses the initial stop. Midpoint is a visual reference.","Illustrative only. Violet shading denotes the overnight range; dotted midpoint is never traded. Actual estimated fills can precede the indicator's confirmed-close marker. Initial and delayed reset stops have distinct line styles. No screenshot prices or unexplained markings are inferred.",artifact="protocol.md",draw=illustrative_guide)
    metrics=[]
    for metric_index,key in enumerate(("eligible_days","executable_fills","completed","censored","net_dollars","expectancy_r","win_rate","max_drawdown_dollars")):
        spec=column_spec(key)
        metric={"label":spec["label"],"value":overall[key],"format":spec.get("format","number"),"precision":spec.get("precision",0)}
        if spec.get("unit"): metric["unit"]=spec["unit"]
        metric["note"]="One-contract standardized baseline; closed results use completed trades."
        metrics.append(metric)
        ev.binding("tables/cohorts.csv",overall_index,key,"baseline",metric_index=metric_index,value=overall[key])
    sections.append({"id":"baseline","kind":"metrics","title":"Baseline breakout results","items":metrics,"referenceIds":["cohorts"]})
    common=["year","session","side"]
    table_sets=[
        ("support","Eligible days, accepted fills and unknown evidence",["eligible_days","valid_ranges","accepted_breakouts","executable_fills","completed","censored","no_trade_days","unknown_days","exclusions"], ["Day metrics apply only to the all-session combined row. The day roster is anchored at broker 07:00 converted to New York, rather than inventing a session for an unfilled day.","Unknown days include censored accepted trades and opportunities whose fill/outcome is unobserved. Do not add these overlapping counts to censored fills.","Valid ranges can include weekends with no entry window and the first loaded day; they are not synonymous with eligible days."]),
        ("profit","P&L and net outcome denominators",["wins","losses","breakevens","win_rate","gross_points","gross_dollars","net_points","net_dollars","cost_dollars"],["Gross here is the raw-price movement along the primary scenario's reset-stop path. It is not the independent zero-cost backtest; that separately executed scenario is below.","Net win rate = saved net wins / all completed trades, including breakevens. Net points = net dollars / $100 per point."]),
        ("risk","Risk-normalized results and payoff",["net_r","r_denominator","invalid_r","expectancy_r","source_style_net_r","source_style_r_denominator","profit_factor","payoff_ratio","max_losing_streak"],["Study R uses positive directional actual-fill to initial boundary stop risk frozen at fill; source-style R uses the active stop risk separately.","Undefined R stays unavailable and affects only R denominators. Executed dollars and costs remain retained. Profit factor is winning dollars / absolute losing dollars; with no losses it is unavailable.","Breakeven is |net dollars| ≤ 1e-8 and resets the primary losing streak."]),
        ("trade-path","Trade excursions, holding time and exits",["mfe_points","mae_points","holding_minutes","median_holding_minutes","stop_exits","timed_exits","ambiguous","mean_minutes_since_start","distinct_broker_days"],["MFE and MAE include only the chosen OHLC path after actual estimated fill and before exit. Censored paths are incomplete and excluded from completed-trade means.","Intraminute fill time is bounded by its observed minute; exact tick timing and native TradingView parity are unavailable."]),
        ("uncertainty","Trade size, drawdown and uncertainty",["mean_net_dollars","median_net_dollars","average_win_dollars","average_loss_dollars","max_drawdown_dollars","mean_dollars_low","mean_dollars_high","expectancy_r_low","expectancy_r_high"],["95% intervals for mean net dollars and mean valid R use frozen four-calendar-week block resampling. They are historical uncertainty summaries, not forward guarantees.","An annual row has its own within-entry-year closed-P&L path. The all-year row has full-history drawdown. No subgroup profit factor or percentage is averaged."]),
        ("win-support","Win-rate uncertainty and saved numerator support",["wins","completed","win_rate","win_rate_low","win_rate_high","win_sum_dollars","loss_sum_dollars","entry_share","quantity_skips"],["Win-rate limits are Wilson 95% intervals. Entry share uses all accepted actual entries over the full history, including censored outcomes, rather than a conditional-year denominator.","Quantity skips in this standardized one-contract view are separate from the source account's two skipped side orders per observed-chart opportunity day."]),
    ]
    for sid,title,fields,notes in table_sets:
        sections.append(ev.table(sid,title,"tables/cohorts.csv",cohorts,common+fields,notes=notes))
        if sid=="support":
            sections.append(ev.table("day-disposition","Every eligible day has a saved disposition","tables/day-disposition.csv",disposition,list(disposition[0]),filters=False,notes=["These mutually exclusive eligible-day classes sum to eligible days: completed fill, censored accepted fill, fully observed no trade, or an unobserved first-fill opportunity.","Unknown days in the cohort table overlap two classes here: censored-fill days plus unobserved first-fill days. They are not an additional disjoint class.","Annual day disposition uses the New York broker-07:00 decision-year anchor; trade performance uses actual fill year."]))
    figure("equity-path","Cumulative net P&L and drawdown","equity-path","Two saved closed-trade paths show cumulative net dollars and drawdown below the prior peak over covered history.","Full-history closed-trade net P&L and drawdown in USD, one GC contract, $2.50 per side and one adverse tick per fill. Censored/open trades have no invented endpoint P&L. Annual drawdown is distinct.","tables/equity.csv",list(range(len(equity))),["exit_time","cumulative_net_dollars","drawdown_dollars"],lambda path:equity_chart(path,equity))
    sections.append(text("annual","Annual performance",annual_finding+"\n\nTrade year follows actual estimated entry time in America/New_York, including Asia entries after midnight. The whole result remains attributed to that entry year even when the exit is later. The table below gives annual support, coverage and within-year drawdown; the three controls above also select each annual/session/side row.",["cohorts"]))
    sections.append(ev.table("annual-table","Annual coverage and within-year drawdown","tables/cohorts.csv",cohorts,["year","completed","censored","net_dollars","max_drawdown_dollars","eligible_days","day_coverage_start","day_coverage_end","entry_coverage_start","entry_coverage_end","partial_year"],selected=annual_indices,filters=False,notes=["Day-roster dates show declared calendar coverage, not proof of every minute. Actual-entry start/end are separate New York fill timestamps. First observed data begin January 2018; its first loaded broker day is excluded. The 2026 year is partial and ends September 18.","Eligible-day year uses the New York 07:00 broker decision anchor; trade cohorts use actual New York fill year. A broker roster date can fall in the neighboring New York decision year; these are distinct calendar anchors."]))
    coverage_fields=["year","actual_minute_start","actual_minute_end","partial_year"]
    coverage_rows=[{key:row[key] for key in coverage_fields} for row in audit["annual"]]
    for i,row in enumerate(coverage_rows):
        for key,value in row.items():
            ev.bindings.append({"section":"observed-annual-coverage","row_index":i,"key":key,"source_artifact":"input-audit/input-summary.json","source_pointer":f"/annual/{i}/{key}","value_type":"boolean" if isinstance(value,bool) else "number" if isinstance(value,(int,float)) else "string"})
    sections.append({"id":"observed-annual-coverage","kind":"table","title":"Observed annual input coverage","description":"Source coverage by fixed UTC+3 broker year, separate from actual New York entry-year performance.","columns":[{"key":"year","label":"Broker year","format":"number","precision":0},{"key":"actual_minute_start","label":"First observed minute (UTC)"},{"key":"actual_minute_end","label":"Last observed minute (UTC)"},{"key":"partial_year","label":"Partial calendar year"}],"rows":coverage_rows,"notes":["An interval between first/last observations does not imply complete data. The causal range audit removes incomplete evidence before orders and retains later missing outcomes as censored.","Annual performance follows New York actual fill year; this source-coverage table follows broker year. 2018 retains the full annual roster with first-loaded-day exclusion; 2026 ends September 18."],"referenceIds":["input-summary"]})
    figure("annual-chart","Annual net P&L","annual-net","Nine bars show positive and negative annual net dollar P&L; 2026 carries a partial-year marker.","Saved combined-side annual net P&L, USD, one GC contract and primary assumed costs. An asterisk identifies partial 2026; annual support is shown in the table.","tables/cohorts.csv",annual_indices,["year","net_dollars","partial_year"],lambda path:bar_chart(path,"Annual net P&L",[r["year"]+(" *" if r["partial_year"] else "") for r in annual],[r["net_dollars"] for r in annual],"One GC contract; $2.50 / side + one adverse tick / fill; * partial 2026"))
    sections.append(text("entry-sessions","Entry sessions and timing","Reporting uses America/New_York with DST: Asia [20:00,02:00 next day), London [02:00,09:00), New York [09:30,16:00), and Outside for all remaining times, including 09:00–09:30. Starts are included and ends excluded. These analytical windows do not filter eligibility. Asia after midnight uses its actual New York date/year.\n\nAll session/hour/weekday counts use the actual estimated fill minute rather than the signal-close alert time. Whole trade P&L stays in the entry cohort. Zero-support sessions and weekdays remain visible; missing outcomes remain censored. The baseline outcome tables above select Year, Entry session and Side independently from saved rows.",["cohorts","timing"]))
    session_indices=[i for i,r in enumerate(cohorts) if r["year"]=="all" and r["side"]=="combined" and r["session"]!="all"]
    session_rows=[cohorts[i] for i in session_indices]
    sections.append(ev.table("session-table","Overall entry-session counts and conditional performance","tables/cohorts.csv",cohorts,["session","executable_fills","entry_share","completed","censored","net_dollars","mean_net_dollars","win_rate","expectancy_r","r_denominator"],selected=session_indices,filters=False,notes=["Count and share include every accepted actual fill, including censored trades. Conditional net performance uses completed trades only; its R denominator uses defined R only."]))
    figure("session-chart","Entry distribution by session","session-counts","Four session bars retain Asia, London, New York and Outside counts, including low or zero support.","Number of all actual accepted entries, including censored outcomes, by New York reporting session. Counts are saved evidence; percentages appear in the adjacent table.","tables/cohorts.csv",session_indices,["session","executable_fills"],lambda path:bar_chart(path,"Actual entry distribution by session",[r["session"] for r in session_rows],[r["executable_fills"] for r in session_rows],"New York reporting windows; actual estimated fill time, including censored trades",ylabel="Entries"))
    heat_indices=[i for i,r in enumerate(cohorts) if r["year"]!="all" and r["side"]=="combined" and r["session"]!="all"]
    figure("year-session-chart","Year-by-session performance","year-session-net","A labeled grid shows net dollar P&L for every year and entry session, with unavailable cells retained.","Net USD assigned wholly to each actual-entry year and session, combined sides, primary assumed costs. This is a visual selection of saved rows; full conditional statistics remain available in the Year/Entry session/Side controls.","tables/cohorts.csv",heat_indices,["year","session","net_dollars"],lambda path:heatmap(path,cohorts))
    hour_indices=[i for i,r in enumerate(timing) if r["dimension"]=="hour" and r["side"]=="combined"]
    hour_rows=[timing[i] for i in hour_indices]
    figure("hour-chart","Entry distribution by New York hour","entry-hours","Twenty-four bars show actual estimated entry count for every New York hour, including empty hours.","Saved entry counts by America/New_York hour with DST, including censored entries. The separate timing tables retain conditional net performance and weekday support.","tables/timing.csv",hour_indices,["bucket","executable_fills"],lambda path:bar_chart(path,"Actual entry distribution by New York hour",[str(r["bucket"]) for r in hour_rows],[r["executable_fills"] for r in hour_rows],"All accepted fills; hour boundaries follow America/New_York including DST",ylabel="Entries",colors=[COLORS[0]]))
    for sid,title,fields in [("timing-support","Hour and weekday support",["dimension","bucket","side","executable_fills","completed","censored","entry_share","mean_minutes_since_start","win_rate","wins","losses"]),("timing-performance","Hour and weekday conditional net performance",["dimension","bucket","side","net_dollars","mean_net_dollars","expectancy_r","r_denominator","profit_factor","max_drawdown_dollars","holding_minutes"] )]:
        section=ev.table(sid,title,"tables/timing.csv",timing,fields,filters=False,notes=["Selections reveal saved hour or weekday rows; they do not recompute the baseline. Share is relative to all actual accepted history entries; completed and valid-R denominators remain distinct."])
        section["rowFilters"]=[{"key":"dimension","label":"Timing view","defaultValue":"hour"},{"key":"side","label":"Side","defaultValue":"combined"}]
        sections.append(section)
    side_indices=[i for i,r in enumerate(cohorts) if r["year"]=="all" and r["session"]=="all" and r["side"]!="combined"]
    figure("side-chart","Long and short comparison","long-short-net","Separate bars show saved long and short net dollar totals under identical fixed settings and costs.","Full-history net USD by side; actual entry cohorts retain censored counts in the selectable tables. Both sides use one GC contract and the same primary assumed costs.","tables/cohorts.csv",side_indices,["side","net_dollars"],lambda path:bar_chart(path,"Long and short net P&L",[cohorts[i]["side"].capitalize() for i in side_indices],[cohorts[i]["net_dollars"] for i in side_indices],"One GC contract; $2.50 / side + one adverse tick / fill"))
    methods=("The primary validated-native approximation preserves 15-minute order decisions and stop-update timing while walking observed same-contract one-minute OHLC. The first boundary touch fills at its level, or an already crossed opening gap fills at the observed open, with adverse transaction slippage. The initial 1% stop is boundary-anchored and tick-rounded; only a surviving entry candle resets it from the actual slipped fill at that candle's close. A same-candle stop cannot be rescued by that reset. A crossed reset queues the following observed open. Evening exit is queued by the close preceding broker 20:00 and normally executes at the 20:00 opening. Market-first priority for competing timed/stop exits is an authored convention. No target, trailing stop, guard or extra trade is used.\n\n"
             "One-minute OHLC cannot prove tick order. The primary nearer-extreme-first path uses the indicator's authored low-first tie; high-first and low-first alternatives retain ordering uncertainty. Their saved completed P&L totals coincide here, while excursions can differ. This is not native TradingView validation. The separate native observed-chart and whole-15-minute OHLC models preserve stale orders through gaps; the primary quality overlay can censor missing evidence. Those source-model rows have a different observed-range population and must not be interpreted as paired profit sensitivities or evidence of executable profit. The indicator's fallback exits are not silently substituted into the native baseline.\n\n"
             "Assumed futures costs were frozen before outcomes: $2.50 per contract per side and one adverse 0.1-point tick per fill. Exact broker tariffs are unavailable. The separately executed zero-cost row uses zero fees/slippage; net zero-, one- and two-tick rows use the stated fees. Entry slippage can change the surviving-candle reset stop, so these are independent fixed executions. Raw-price gross in the primary cohort table refers to that primary path and differs from the separate zero-cost run.")
    sections.append(text("methods","Execution assumptions, robustness and methods",methods,["scenarios","config","protocol"]))
    high_index=next(i for i,r in enumerate(scenarios) if r["scenario"]=="high-first-one-tick")
    low_index=next(i for i,r in enumerate(scenarios) if r["scenario"]=="low-first-one-tick")
    claims.append({"id":"ordering-same-pnl","target":{"section":"methods","field":"body"},"text":"Their saved completed P&L totals coincide here", "conditions":[{"source_artifact":"tables/scenarios.csv","source_row":high_index,"source_column":"net_dollars","operator":"eq","other_cell":{"source_artifact":"tables/scenarios.csv","source_row":low_index,"source_column":"net_dollars"}}],"sources":[]})
    sections.append(ev.table("scenario-table","Prespecified costs and execution-model comparisons","tables/scenarios.csv",scenarios,["scenario","completed","censored","ambiguous","net_dollars","mean_net_dollars","net_r","r_denominator","win_rate","profit_factor","dd_dollars","fills"],filters=False,notes=["Primary, zero/one/two adverse tick costs and high-/low-first paths use the same quality population. Native observed-chart and source 15m rows deliberately use different range eligibility; compare their semantics and support before reading their totals.","The source-account row has no fills. Its unavailable trade ratios/P&L sums are not evidence of a zero-expectancy strategy; the separate account reproduction records unchanged capital and zero realized orders."]))
    account=json.loads((stage/"source-account.json").read_text())
    ev.sources["source-account.json"]=sha(stage/"source-account.json")
    account_text=(f'The separate source reproduction starts with ${account["initial_capital_dollars"]:,.0f}, 1% equity risk, 10x leverage cap and whole-GC quantity flooring. '
                  f'It produced {account["executable_fills"]:,} executable fills, {account["quantity_skip_side_days"]:,} skipped side-day quantities across '
                  f'{account["quantity_skip_days"]:,} broker days, and ${account["realized_pnl_dollars"]:,.0f} realized P&L. Capital remains '
                  f'${account["ending_capital_dollars"]:,.0f} before external cashflows. No fractional GC order or silent increase in capital is invented. '
                  'The source $0.40 cash-per-order setting is retained as source behavior, not presented as realistic futures costs. Standardized one-contract net dollars cannot be described as returns achievable by this source account.')
    sections.append(text("source-account","Separate source-account reproduction",account_text,["source-account","config"]))
    claims.append({"id":"source-account-sizing","target":{"section":"source-account","field":"body"},"text":account_text,
                   "conditions":[{"source_artifact":"source-account.json","source_pointer":"/executable_fills","operator":"eq","value":0},{"source_artifact":"source-account.json","source_pointer":"/quantity_skip_days","operator":"gt","value":0},{"source_artifact":"source-account.json","source_pointer":"/realized_pnl_dollars","operator":"eq","value":0}],
                   "sources":[{"source_artifact":"source-account.json","source_pointer":"/"+key,"display":{"style":"dollars" if key.endswith("dollars") else "number","precision":0,"grouping":True}} for key in ("initial_capital_dollars","executable_fills","quantity_skip_side_days","quantity_skip_days","realized_pnl_dollars","ending_capital_dollars")]})
    example_indices=[next(i for i,r in enumerate(trades) if r["trade_id"]==s["trade_id"]) for s in selections]
    bars_indices=list(range(len(bars)))
    figure("empirical-examples","Pinned observed winning and losing examples","observed-examples","Four panels retain the earliest completed net-winning and net-losing trade per side, observed one-minute extrema and close trace, range, actual fill, initial/reset stops and exit.","Selection is mechanical: earliest chronological completed net win and net loss per side, with no visual selection. Pinned same-contract observed minute bars are faint extrema plus a close trace. Violet range extrema are the selected overnight max-high/min-low; dotted midpoint is visual only. Fill and exit markers and initial/reset stop levels/timing trace to the saved primary ledger. Exact tick order remains unavailable.","tables/selected-example-bars.csv",bars_indices,["timestamp","open","high","low","close","contract","trade_id"],lambda path:empirical_examples(path,bars,selections),extra_sources=[{"source_artifact":"tables/primary-trades.csv","sha256":ev.sources["tables/primary-trades.csv"],"source_rows":example_indices,"source_columns":["trade_id","entry_time","initial_stop","reset_stop","reset_stop_active_at","exit_time","entry_price","exit_price"]},{"source_artifact":"example-selection.json","sha256":ev.sources["example-selection.json"]}])
    sections.append(ev.table("example-ledger","Selected example stop and fill ledger","tables/primary-trades.csv",trades,["trade_id","side","entry_time","initial_stop","initial_stop_active_at","reset_stop","reset_stop_active_at","risk_initial_dollars","source_risk_dollars","exit_reason","net_dollars"],selected=example_indices,filters=False,notes=["These are four explanatory examples, not representative performance samples. Initial and reset levels and activation instants remain separately saved. Stop risk units are USD for one contract; UTC times retain minute precision bounds in the private evidence ledger."]))
    quality=(f'Pinned input is {lock["dataset_id"]} version {lock["version"]}, unadjusted GC leader bars with same-contract execution and roll barriers. '
             f'Observed retained minutes run from {audit["first_observed_minute"]} through {audit["last_observed_minute"]}; modeled last availability is {audit["last_modeled_available_at"]}. '
             'The retained dataset ends in September 2026 and does not extend through the October approval date. All selected partition, manifest, roll and instrument-master identities are frozen in the input lock. GC is $100 per point, 0.1-point tick worth $10, minimum and step one contract.\n\n'
             f'The input audit checks {audit["selected_minute_rows"]:,} observed minutes and {audit["aggregation_check"]["observed_bars"]:,} observed 15-minute candles. '
             f'It records {audit["missing_qualified_expected_minutes"]:,} missing qualified expected minutes and {audit["missing_uncertified_holiday_nominal_minutes"]:,} missing uncertified-holiday nominal minutes. '
             'Omitted trade bars may be no-trade intervals or delivery gaps; absent evidence is never filled or silently inferred as a closure. Scheduled maintenance/weekends are separate. Historical annual holiday/early-close certification is unavailable; candidate sessions are conservatively excluded before orders. Known range evidence determines causal eligibility; later missing outcomes remain censored instead of deleting accepted fills.\n\n'
             'This conservative completeness requirement leaves a restricted historical sample. New York and Outside entry windows have sparse support; do not turn their conditional means into broad session conclusions. Modeled available_at is candle completion, not measured vendor or roll-map receipt latency. Native TradingView compilation/replay, tick ordering and raw-source reconstruction remain unverified. The wider Bhishma raw/roll prerequisite failures persist; selected published GC bytes and aggregation passed their own input checks.')
    sections.append(text("inputs-and-limits","Pinned inputs, coverage and material limitations",quality,["inputs-lock","input-summary"]))
    coverage_sources=[]
    for key in ("first_observed_minute","last_observed_minute","last_modeled_available_at","selected_minute_rows","missing_qualified_expected_minutes","missing_uncertified_holiday_nominal_minutes"):
        item={"source_artifact":"input-audit/input-summary.json","source_pointer":"/"+key,"value_type":"string" if isinstance(audit[key],str) else "number"}
        if not isinstance(audit[key],str): item["display"]={"style":"number","precision":0,"grouping":True}
        coverage_sources.append(item)
    coverage_sources.append({"source_artifact":"input-audit/input-summary.json","source_pointer":"/aggregation_check/observed_bars","value_type":"number","display":{"style":"number","precision":0,"grouping":True}})
    claims.append({"id":"input-coverage","target":{"section":"inputs-and-limits","field":"body"},"text":quality,"conditions":[],"sources":coverage_sources})
    sparse_indices=[next(i for i,r in enumerate(cohorts) if r["year"]=="all" and r["side"]=="combined" and r["session"]==s) for s in ("New York","Outside")]
    claims.append({"id":"sparse-entry-sessions","target":{"section":"inputs-and-limits","field":"body"},"text":"New York and Outside entry windows have sparse support", "conditions":[{"source_artifact":"tables/cohorts.csv","source_row":i,"source_column":"executable_fills","operator":"lt","value":limit} for i,limit in zip(sparse_indices,(30,5))],"sources":[]})
    sections.append(text("phase2","Phase 2 planned","Midpoint, boundary reclaim, other interior-range entries, re-entry, additional trades, pyramiding, new entry filters and optimization remain unimplemented and uncomputed. The midpoint in every guide is a visual reference only. H10 signal-close diagnostics are also uncomputed and would be auxiliary price-path statistics, not realized trade returns.\n\nPhase 2 should reuse the frozen Phase 1 protocol, input pins and baseline ledgers. All baseline years opened and published here are prior exposure and cannot later be called untouched holdouts. A new instruction and a separately frozen protocol are required for alternative-entry research.",["protocol","config"]))
    if len(sections)>30:
        raise ValueError("Report exceeds the section bound")
    downloads=[]
    selected_csvs=[
        ("performance","cohort-performance.csv","tables/cohorts.csv",list(range(len(cohorts))),["year","session","side","accepted_breakouts","executable_fills","completed","censored","ambiguous","wins","losses","breakevens","win_rate","net_points","net_dollars","gross_points","gross_dollars","cost_dollars","profit_factor","payoff_ratio","mean_net_dollars","median_net_dollars","max_drawdown_dollars","eligible_days","unknown_days"]),
        ("risk-uncertainty","risk-and-uncertainty.csv","tables/cohorts.csv",list(range(len(cohorts))),["year","session","side","net_r","r_denominator","invalid_r","expectancy_r","source_style_net_r","source_style_r_denominator","win_rate_low","win_rate_high","mean_dollars_low","mean_dollars_high","expectancy_r_low","expectancy_r_high","average_win_dollars","average_loss_dollars","mfe_points","mae_points","holding_minutes","stop_exits","timed_exits","max_losing_streak","entry_share"]),
        ("timing","entry-timing.csv","tables/timing.csv",list(range(len(timing))),["dimension","bucket","side","executable_fills","completed","censored","wins","losses","breakevens","win_rate","entry_share","net_dollars","mean_net_dollars","expectancy_r","r_denominator","profit_factor","max_drawdown_dollars","holding_minutes","mean_minutes_since_start"]),
        ("scenarios","execution-scenarios.csv","tables/scenarios.csv",list(range(len(scenarios))),list(scenarios[0])),
    ]
    for did,name,artifact,indices,columns in selected_csvs:
        if len(columns)>24:
            raise ValueError("Download exceeds 24 columns")
        target=stage/"downloads"/name
        target.parent.mkdir(exist_ok=True)
        with (stage/artifact).open(newline="") as stream:
            raw=list(csv.DictReader(stream))
        with target.open("x",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=columns,extrasaction="ignore")
            writer.writeheader()
            writer.writerows({key:raw[i][key] for key in columns} for i in indices)
        info={"id":did,"path":"downloads/"+name,"label":name.replace("-"," ").removesuffix(".csv").title(),"description":"Exact saved-cell column selection; no statistics recalculated.","population":"Explicit saved overall, entry-year/session/side or timing/scenario cohorts; zero-support rows retained.","units":"USD, GC points and R; win/entry-share rates are ratios, not whole percentages.","scope":"Standardized primary assumed-cost results unless the row explicitly names a separate execution scenario; source account remains separate.","mediaType":"text/csv","sha256":sha(target),"rowCount":len(indices),"columns":columns,"source":{"runId":run_id,"artifact":artifact,"sha256":ev.sources[artifact]}}
        downloads.append(info)
        ev.downloads.append({"id":did,"path":info["path"],"source_artifact":artifact,"source_rows":indices,"columns":columns,"sha256":info["sha256"],"source_sha256":ev.sources[artifact]})
    references=[{"id":reference_id(artifact),"kind":"saved-artifact","label":artifact,"title":"Frozen Phase 1 saved evidence: "+artifact,"runId":run_id,"artifact":artifact,"sha256":digest} for artifact,digest in ev.sources.items() if artifact!="input-audit/input-summary.json"]
    report={"schemaVersion":"1.1","id":publication_id,"title":"GC- Overnight Breakout 15M — Phase 1","summary":"Fixed overnight-boundary breakout on pinned GC bars: standardized one-contract net results, annual and actual-entry-session cohorts, independent source-account sizing and explicit execution/input limitations.","publishedAt":published_at,"source":{"producer":"sahadeva","runId":run_id},"sections":sections,"references":references,"downloads":downloads,"notes":["Saved baseline evidence only; browser controls select authored rows without calculating research statistics.","The source account and standardized one-contract dollars are distinct. Costs are assumed scenarios, not the user's broker charges.","Phase 2 and H10 diagnostics remain uncomputed. Native TradingView equivalence is unverified."]}
    source_map={"schema_version":"study23.web-source-cells/v1","run_id":run_id,"source_row_base":0,"source_artifacts":[{"path":artifact,"sha256":digest} for artifact,digest in ev.sources.items()],"bindings":ev.bindings,"figures":ev.figures,"downloads":ev.downloads,"claims":claims,"authored_assumptions":{"source_artifacts":["config.json","protocol.md","inputs.lock.json"],"scope":"Frozen settings and definitions copied into prose; source screenshot used only for design cues, never as numerical evidence."}}
    inventory=snapshot/"figure-render-inputs.json"
    inventory.write_bytes(json_bytes(figure_specs))
    result=subprocess.run(["node",str(snapshot/"rasterize_figures.mjs"),str(package_root),str(inventory)],check=True,capture_output=True,text=True)
    for figure in ev.figures:
        figure["image_sha256"]=sha(stage/figure["path"])
        figure["svg_sha256"]=sha((stage/figure["path"]).with_suffix(".svg"))
    (stage/"publication.json").write_bytes(json_bytes(report))
    (stage/"source-map.json").write_bytes(json_bytes(source_map))
    generation={"producer_version":VERSION,"run_id":run_id,"command":sys.argv,"python":sys.version,"producer_snapshot":producer_records,"figure_runtime":json.loads(Path(str(inventory)+".runtime.json").read_text()),"stdout":result.stdout,"stderr":result.stderr,"sections":len(sections),"cell_bindings":len(ev.bindings),"figures":len(ev.figures),"downloads":len(downloads),"source_artifacts":source_map["source_artifacts"],"verification":"Awaiting independent cell/CSV/figure review; this producer does not certify itself."}
    (stage/"publication-generation.json").write_bytes(json_bytes(generation))
    return {"publication_id":publication_id,"sections":len(sections),"cell_bindings":len(ev.bindings),"figures":len(ev.figures),"downloads":len(downloads)}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--publication-id",required=True)
    parser.add_argument("--published-at",required=True)
    parser.add_argument("--node-package-root",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(create_publication(args.stage,args.run_id,args.publication_id,args.published_at,args.node_package_root),indent=2))
