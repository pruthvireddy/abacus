"""Render the offline report from saved yearly statistics, never market bars."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_provenance import run_phase

import pandas as pd


CSS = """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e9edf2;background:#0c1420}
*{box-sizing:border-box}body{margin:0;line-height:1.5}main{max-width:1330px;margin:auto;padding:34px 28px 100px}
.top{border:1px solid #34505c;background:linear-gradient(130deg,#12343a,#172739 58%,#172134);border-radius:22px;padding:34px 38px;margin-bottom:22px;position:relative;overflow:hidden}
.eyebrow{color:#77d2c0;text-transform:uppercase;letter-spacing:.16em;font-size:.76rem;font-weight:800}.top h1{font-size:clamp(2rem,4vw,3.55rem);line-height:1.08;margin:12px 0 18px;max-width:20ch;letter-spacing:-.035em}.top p{max-width:78ch;color:#c3d2da;margin:0}
.pill{display:inline-block;margin:22px 8px 0 0;border:1px solid #4a6c74;color:#c5e5e2;background:#102d33;border-radius:999px;padding:5px 12px;font-size:.82rem}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin:18px 0 24px}.card,.panel{border:1px solid #2b3e50;background:#152334;border-radius:15px}.card{padding:17px 19px}.card small{display:block;color:#9eafbf;font-size:.76rem;text-transform:uppercase;letter-spacing:.08em}.card strong{display:block;font-size:1.8rem;letter-spacing:-.04em;margin-top:6px}.card span{font-size:.78rem;color:#a8b8c4}
.panel{padding:25px;margin:22px 0}.panel h2{margin:0 0 7px;font-size:1.35rem;letter-spacing:-.015em}.panel p{color:#adbecc;max-width:104ch;margin:7px 0 15px}.controls{display:flex;gap:14px;flex-wrap:wrap;margin:22px 0 8px}.controls label{color:#aebdca;font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;display:flex;flex-direction:column;gap:6px}select{background:#0d1a29;border:1px solid #3c5868;color:#f0f6fa;border-radius:8px;padding:10px 13px;font-size:1rem;min-width:160px}
.table-wrap{overflow:auto;border:1px solid #2b3e50;border-radius:10px}table{border-collapse:collapse;width:100%;white-space:nowrap;font-variant-numeric:tabular-nums;font-size:.87rem}th,td{padding:10px 12px;border-bottom:1px solid #27394a;text-align:right}th{position:sticky;top:0;background:#21364a;color:#cce0ec;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:#192b3e;font-weight:700}tr:hover td{background:#20384a}tr:hover td:first-child{background:#244154}.year-current{color:#8be1c9}.muted{color:#91a2b0}.positive{color:#8be1c9}.negative{color:#f3b7a7}
.bars{display:grid;gap:8px;margin:20px 0}.bar-row{display:grid;grid-template-columns:68px 1fr 90px;gap:12px;align-items:center;font-size:.84rem;color:#b9c9d5}.bar-track{display:flex;flex-direction:column;gap:2px;height:22px}.bar-mfe,.bar-mae{height:10px;border-radius:999px}.bar-mfe{background:#48b8a2}.bar-mae{background:#e8a96b}.legend{display:flex;gap:18px;color:#aebfca;font-size:.82rem}.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}.formula{background:#0e1c2b;border-left:3px solid #65c4b4;padding:14px 18px;border-radius:3px;font-family:ui-monospace,SFMono-Regular,monospace;color:#dce7ec;overflow:auto}.two{display:grid;grid-template-columns:1fr 1fr;gap:22px}a{color:#80d0c3}ul{color:#b8c7d3;padding-left:20px}li{margin:7px 0}footer{color:#8194a5;font-size:.8rem;padding-top:20px;border-top:1px solid #344758}
@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}main{padding:18px 13px 60px}.top{padding:25px}}
"""


def _render(stage: Path, output_dir: Path | None = None) -> None:
    if not (stage / "metrics.json").exists():
        raise ValueError("saved metrics missing")
    stats = pd.read_csv(stage / "tables/yearly.csv")
    metrics = json.loads((stage / "metrics.json").read_text())
    if len(stats) != metrics["statistic_rows"] or len(stats) != 595:
        raise ValueError("statistics table count mismatch")
    default = stats.loc[(stats.cooldown == 10) & (stats.horizon == 20)].sort_values("year", ascending=False)
    if len(default) != 17:
        raise ValueError("missing year in default view")
    latest = default.loc[default.year == 2026].iloc[0]
    prior = default.loc[default.year == 2025].iloc[0]
    out = stage if output_dir is None else output_dir
    out.mkdir(parents=True, exist_ok=True)
    total_n = int(default.valid_n.sum())
    overall_mae = float((default.valid_n * default.mean_mae).sum() / total_n)
    overall_mfe = float((default.valid_n * default.mean_mfe).sum() / total_n)
    overall_positive = float((default.valid_n * default.terminal_positive_rate).sum() / total_n)
    fallback_rows = "".join(
        "<tr>" +
        f"<td class='{'year-current' if r.year == 2026 else ''}'>{int(r.year)}{' YTD' if r.year == 2026 else ''}</td>" +
        f"<td>{int(r.raw_candidates):,}</td><td>{int(r.accepted_signals):,}</td><td>{int(r.valid_n):,}</td>" +
        f"<td>{r.mean_mae:.2f}</td><td>{r.p90_mae:.2f}</td><td>{r.mean_mfe:.2f}</td><td>{r.p90_mfe:.2f}</td>" +
        f"<td>{r.mean_terminal:.2f}</td><td>{100*r.terminal_positive_rate:.1f}%</td>" +
        f"<td>{int(r.accepted_signals-r.valid_n):,}</td></tr>"
        for r in default.itertuples())
    chart_max = max(float(default.mean_mae.max()), float(default.mean_mfe.max()))
    fallback_bars = "".join(
        f"<div class='bar-row'><span>{int(r.year)}</span><div class='bar-track'>"
        f"<div class='bar-mfe' style='width:{100*r.mean_mfe/chart_max:.2f}%'></div>"
        f"<div class='bar-mae' style='width:{100*r.mean_mae/chart_max:.2f}%'></div>"
        f"</div><span>{r.mean_mfe:.1f} / {r.mean_mae:.1f}</span></div>"
        for r in default.itertuples())
    data_json = stats.to_json(orient="records", double_precision=10)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GC lower outer band | MAE/MFE by year</title><style>{CSS}</style></head>
<body><main><header class="top"><div class="eyebrow">Abacus / Sahadeva / Study 12</div>
<h1>What follows a GC close at the outer lower band?</h1>
<p>Five-minute GC, long-side path study. Explore mean adverse excursion (MAE) and mean favorable excursion (MFE) after a confirmed close at or below the indicator’s three-sigma lower band.</p>
<span class="pill">2010–2026 YTD</span><span class="pill">5 cooldowns × 7 horizons</span><span class="pill">Retrospective · descriptive</span></header>
<section class="grid" aria-label="Selected cohort summary">
<div class="card"><small>Valid signals</small><strong id="card-n">{total_n:,}</strong><span>Selected cooldown and horizon</span></div>
<div class="card"><small>Mean MAE</small><strong id="card-mae">{overall_mae:.2f}</strong><span>GC price points · downside from next open</span></div>
<div class="card"><small>Mean MFE</small><strong id="card-mfe">{overall_mfe:.2f}</strong><span>GC price points · upside from next open</span></div>
<div class="card"><small>Terminal positive</small><strong id="card-positive">{100*overall_positive:.1f}%</strong><span>Last close above next open; before costs</span></div></section>
<section class="panel"><h2>What the default view shows</h2>
<p>With a 10-bar cooldown and a 20-bar horizon, 2026 YTD has <strong>{int(latest.valid_n):,} valid paths</strong>: mean MAE <strong>{latest.mean_mae:.2f}</strong> points and mean MFE <strong>{latest.mean_mfe:.2f}</strong> points. In 2025, {int(prior.valid_n):,} valid paths had mean MAE {prior.mean_mae:.2f} and mean MFE {prior.mean_mfe:.2f} points. The large change in point scale calls for volatility-aware interpretation; it does not by itself show a change in trade quality. The table below gives every year and lets you inspect all cooldowns and horizons.</p></section>
<section class="panel"><h2>Explore the requested combinations</h2>
<p>Each cooldown creates a separate signal cohort. A horizon of 20 means the entry bar plus the following 19 contiguous five-minute bars. Choose any requested pair; the table and chart update from saved results.</p>
<div class="controls"><label>Cooldown after signal<select id="cooldown"><option value="0">0 bars · reference</option><option value="5">5 bars</option><option value="10" selected>10 bars</option><option value="20">20 bars</option><option value="30">30 bars</option></select></label>
<label>Excursion horizon<select id="horizon"><option value="5">5 bars · 25 min</option><option value="10">10 bars · 50 min</option><option value="15">15 bars · 75 min</option><option value="20" selected>20 bars · 100 min</option><option value="30">30 bars · 150 min</option><option value="50">50 bars · 250 min</option><option value="100">100 bars · 500 min</option></select></label></div>
<div class="table-wrap"><table><thead><tr><th>Signal year</th><th>Raw closes</th><th>After cooldown</th><th>Valid paths</th><th>Mean MAE</th><th>MAE p90</th><th>Mean MFE</th><th>MFE p90</th><th>Mean terminal</th><th>Terminal +</th><th>Excluded</th></tr></thead><tbody id="year-rows">{fallback_rows}</tbody></table></div>
<p class="muted">Points are nominal GC price points, so years with different price and volatility regimes are not directly comparable in scale. Excluded is accepted signals without a valid full path at this horizon. Full medians, approximate intervals, and reason counts are in <code>tables/yearly.csv</code>.</p></section>
<section class="panel"><h2>Annual path scale</h2><p>Lengths compare the selected cohort’s mean favorable and adverse extrema, within each calendar year.</p>
<div class="legend"><span><i style="background:#48b8a2"></i>MFE</span><span><i style="background:#e8a96b"></i>MAE</span></div><div id="bars" class="bars">{fallback_bars}</div></section>
<div class="two"><section class="panel"><h2>Signal and entry</h2>
<p>The pasted Pine indicator defines a 225-close EMA and the population standard deviation of the most recent 225 signed <em>close minus EMA</em> residuals. The lower outer band is three sigmas below that EMA. We use the bar’s completed close at or below this band; the script’s separate inner-band re-entry marker is a different rule.</p>
<div class="formula">signal: close[t] ≤ EMA225[t] − 3 × STDEV225(close − EMA225)[t]<br>entry: next complete 5-minute bar's unadjusted open</div>
<p>The band includes the signal close and becomes available at the bar close. There is no intrabar entry at the band.</p></section>
<section class="panel"><h2>What the excursions measure</h2>
<div class="formula">MAE(H) = max(0, entry − min(low[t+1 … t+H]))<br>MFE(H) = max(0, max(high[t+1 … t+H]) − entry)</div>
<p>MAE and MFE are separate extremes. A five-minute OHLC bar does not reveal whether its high or low happened first, so these values cannot be combined into a realizable target-and-stop trade. “Terminal +” is only the fraction whose last close exceeds the entry; it is not a win rate after costs.</p></section></div>
<section class="panel"><h2>Reading the evidence</h2><ul>
<li>Signals after cooldown are based on accepted completed-bar signals. Suppressed candidates do not restart the cooldown. The next eligible signal is C+1 bars after an accepted signal.</li>
<li>Valid paths need complete five-minute bars with continuous timestamps, one raw contract, and one adjustment from signal through the entire horizon. Gaps, partial bars, and cross-contract paths are excluded.</li>
<li>Year is the signal close’s New York calendar year. 2010 starts in June; 2026 ends with the pinned September 18 source data. Yearly sample sizes differ.</li>
<li>The signal uses a final backward-adjusted continuous series. Its earlier chart values can incorporate later roll adjustments and are not point-in-time certified; the adjusted chart may differ from TradingView. Excursions use reconstructed unadjusted selected-contract OHLC.</li>
<li>Overlapping signals and 35 displayed combinations create dependence and selection risk. Approximate week-clustered mean intervals are in the saved table, with no multiple-comparison correction. No fill, spread, slippage, fees, sizing, stop, or exit policy is modeled.</li>
</ul></section>
<footer>Source: Abacus pinned GC five-minute release <code>tv_indicators__dridr_ohlcv_5m__v1</code> and band release <code>gc_ema_deviation_bands__1.0.0</code>. Study 12 protocol v1.0.0. The complete event ledger, config, locks, and checks accompany this report.</footer>
</main><script>const DATA={data_json};
const fmt=(x,d=1)=>x==null?'—':Number(x).toLocaleString('en-US',{{minimumFractionDigits:d,maximumFractionDigits:d}});
const pct=x=>x==null?'—':fmt(100*x,1)+'%';
function draw(){{let c=+document.getElementById('cooldown').value,h=+document.getElementById('horizon').value;
let rows=DATA.filter(r=>r.cooldown===c&&r.horizon===h).sort((a,b)=>b.year-a.year);
let n=rows.reduce((s,r)=>s+r.valid_n,0),mae=rows.reduce((s,r)=>s+r.valid_n*r.mean_mae,0)/n,mfe=rows.reduce((s,r)=>s+r.valid_n*r.mean_mfe,0)/n;
let pos=rows.reduce((s,r)=>s+r.valid_n*r.terminal_positive_rate,0)/n;
document.getElementById('card-n').textContent=fmt(n,0);document.getElementById('card-mae').textContent=fmt(mae,2);document.getElementById('card-mfe').textContent=fmt(mfe,2);document.getElementById('card-positive').textContent=pct(pos);
document.getElementById('year-rows').innerHTML=rows.map(r=>`<tr><td class="${{r.year===2026?'year-current':''}}">${{r.year}}${{r.year===2026?' YTD':''}}</td><td>${{fmt(r.raw_candidates,0)}}</td><td>${{fmt(r.accepted_signals,0)}}</td><td>${{fmt(r.valid_n,0)}}</td><td>${{fmt(r.mean_mae,2)}}</td><td>${{fmt(r.p90_mae,2)}}</td><td>${{fmt(r.mean_mfe,2)}}</td><td>${{fmt(r.p90_mfe,2)}}</td><td class="${{r.mean_terminal>=0?'positive':'negative'}}">${{fmt(r.mean_terminal,2)}}</td><td>${{pct(r.terminal_positive_rate)}}</td><td>${{fmt(r.accepted_signals-r.valid_n,0)}}</td></tr>`).join('');
let max=Math.max(...rows.flatMap(r=>[r.mean_mae,r.mean_mfe]));
document.getElementById('bars').innerHTML=rows.map(r=>`<div class="bar-row"><span>${{r.year}}</span><div class="bar-track"><div class="bar-mfe" style="width:${{(r.mean_mfe/max*100).toFixed(2)}}%"></div><div class="bar-mae" style="width:${{(r.mean_mae/max*100).toFixed(2)}}%"></div></div><span>${{fmt(r.mean_mfe,1)}} / ${{fmt(r.mean_mae,1)}}</span></div>`).join('');}}
document.getElementById('cooldown').addEventListener('change',draw);document.getElementById('horizon').addEventListener('change',draw);draw();</script></body></html>"""
    (out / "report.html").write_text(html)
    if out != stage:
        return
    lines = ["# GC outer lower EMA band: long excursions", "",
             "Study 12, protocol 1.0.0. Descriptive retrospective path analysis; not a trade backtest with costs or an exit rule.", "",
             "The signal is a completed five-minute close at or below EMA225 minus three population standard deviations of signed close-minus-EMA residuals. Entry is the next complete bar's reconstructed unadjusted open. MAE and MFE use H future bars and are separate extrema.", "",
             "## Default view: 10-bar cooldown, 20-bar horizon", "",
             "| Year | Accepted | Valid | Mean MAE (pts) | Mean MFE (pts) | Mean terminal (pts) | Terminal positive |",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in default.iterrows():
        lines.append(f"| {int(r.year)}{' YTD' if r.year == 2026 else ''} | {int(r.accepted_signals)} | {int(r.valid_n)} | {r.mean_mae:.2f} | {r.mean_mfe:.2f} | {r.mean_terminal:.2f} | {100*r.terminal_positive_rate:.1f}% |")
    lines += ["", "## Interpretation", "",
              f"In the default view, 2026 YTD has {int(latest.valid_n)} valid paths and mean MAE/MFE of {latest.mean_mae:.2f}/{latest.mean_mfe:.2f} points, compared with {int(prior.valid_n)} and {prior.mean_mae:.2f}/{prior.mean_mfe:.2f} in 2025. These point scales reflect different price and volatility regimes; their ratio is not an estimate of changing edge.", "",
              "The annual excursion scale changes materially, particularly in 2025–2026. Fixed point targets or stops inferred from pooled years would ignore that regime difference. MAE and MFE alone cannot show whether a stop or target would have filled first, and the terminal-positive rate ignores trading costs. Overlapping paths and the 35 exploratory combinations do not constitute independent confirmation.", "",
              "The final back-adjusted indicator snapshot is retrospective and may differ from TradingView. Paths with missing minutes, partial bars, roll transitions, or changed contracts are unavailable rather than zero. 2010 starts midyear and 2026 is year-to-date through the pinned September 18 bars.", "",
              "## Full evidence", "",
              "See `tables/yearly.csv` for all 595 year/cooldown/horizon cells, medians, p90s, approximate ISO-week clustered mean intervals, and exclusion reasons; `tables/events.parquet` for event-level outcomes; `metrics.json`, `config.json`, and `inputs.lock.json` for definitions and identities. Open `report.html` offline to filter the complete table.\n"]
    (stage / "report.md").write_text("\n".join(lines))
    (stage / "advice.md").write_text("# Dated interpretation — 2026-09-25\n\n"
        "This run describes path excursions after lower-band closes; it does not establish a profitable long strategy. "
        "The first useful next study would freeze a single cooldown, horizon, and executable exit policy; use unadjusted prices, fees, and slippage; and compare with a time-matched GC baseline on later data. "
        "Do not select a stop or target from these same 35 exploratory cells and call the resulting performance validated. "
        "Support and counterevidence are the full annual table, including years with larger mean MAE than MFE and the substantial 2026 volatility scale.\n")


def render(stage: Path, output_dir: Path | None = None) -> None:
    # Historical presentation-only output keeps its existing separate interface.
    if output_dir is not None:
        _render(stage, output_dir)
        return
    study = Path(__file__).resolve().parent
    run_phase(study.parents[1], study.name, stage, "rendering",
              lambda: _render(stage.absolute()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    render(args.stage, args.output.resolve() if args.output else None)


if __name__ == "__main__":
    main()
