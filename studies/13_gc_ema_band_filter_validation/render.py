"""Render a static two-year filter report from saved numerical tables."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_provenance import run_phase

import pandas as pd


LABELS = {
    "unfiltered": "Unfiltered outer-band close",
    "first_outer_close": "First outer-band close",
    "bullish_signal_body": "Bullish signal body",
    "upper_half_close": "Upper-half close",
    "shallow_penetration_025": "Shallow penetration ≤0.25σ",
    "less_falling_ema_050": "EMA slope ≥−0.5σ",
    "nonexpanding_sigma_110": "Sigma growth ≤10%",
    "ny_morning_08_13": "NY 08:00–13:00",
    "first_outer_and_upper_half": "First close + upper half",
    "shallow_and_upper_half": "Shallow + upper half",
}

CSS = """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;color:#e9f0f4;background:#0d1622}
*{box-sizing:border-box}body{margin:0;line-height:1.55}main{max-width:1320px;margin:auto;padding:32px 28px 90px}
header{background:linear-gradient(120deg,#113b3c,#163144 60%,#202a40);border:1px solid #3a6262;border-radius:22px;padding:36px;margin-bottom:22px}
.eyebrow{font-size:.75rem;text-transform:uppercase;letter-spacing:.15em;color:#7cdbcc;font-weight:800}h1{font-size:clamp(2rem,4vw,3.3rem);line-height:1.1;letter-spacing:-.04em;margin:12px 0 16px;max-width:21ch}h2{font-size:1.4rem;letter-spacing:-.02em;margin:0 0 9px}h3{font-size:1.07rem;margin:20px 0 8px}p{color:#b8c8d2;max-width:105ch;margin:8px 0 16px}.lead{font-size:1.07rem;max-width:83ch;color:#d5e4e8}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}.badge{border:1px solid #4b7275;border-radius:999px;background:#0f3037;color:#c7eee5;padding:4px 11px;font-size:.8rem}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.card,.panel{border:1px solid #2e4354;border-radius:15px;background:#172638}.card{padding:18px}.card small{display:block;text-transform:uppercase;letter-spacing:.08em;color:#97aebd;font-size:.75rem}.card strong{display:block;font-size:1.75rem;letter-spacing:-.03em;margin-top:4px}.card span{color:#a9becb;font-size:.78rem}.panel{padding:24px;margin:20px 0}.panel p:last-child{margin-bottom:0}
.table-wrap{overflow:auto;border:1px solid #31495b;border-radius:10px;margin:15px 0}table{border-collapse:collapse;width:100%;white-space:nowrap;font-variant-numeric:tabular-nums;font-size:.86rem}th,td{padding:9px 11px;border-bottom:1px solid #293e50;text-align:right}th{background:#243a4d;color:#d9e7ed;font-size:.73rem;text-transform:uppercase;letter-spacing:.05em}th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:#1a2d40}tr.selected td{background:#1d4b4b}tr.selected td:first-child{background:#1d4b4b}tr:hover td{background:#254153}.note{font-size:.83rem;color:#99afbc}.good{color:#91e0c8}.bad{color:#f0b6a7}.neutral{color:#c5d6df}
.callout{border-left:3px solid #e2ba6a;background:#202c39;padding:14px 17px;border-radius:4px;color:#dde7ea}.split{display:grid;grid-template-columns:1fr 1fr;gap:20px}details{border:1px solid #31495b;border-radius:10px;margin:14px 0;padding:12px 16px}summary{cursor:pointer;color:#cfebe7;font-weight:700}.formula{font-family:ui-monospace,SFMono-Regular,monospace;background:#0f1e2d;padding:13px;border-left:3px solid #6dd0be;color:#e7eff1;overflow:auto}a{color:#88dbcd}ul{color:#b9cad3;padding-left:22px}li{margin:8px 0}footer{border-top:1px solid #354c5d;padding-top:20px;color:#8298a8;font-size:.82rem}
@media(max-width:880px){.grid{grid-template-columns:repeat(2,1fr)}.split{grid-template-columns:1fr}main{padding:15px 11px 50px}header{padding:24px}th,td{padding:7px 8px}}
"""


def f(value: float | None, digits: int = 2) -> str:
    return "—" if value is None or pd.isna(value) else f"{value:,.{digits}f}"


def compare_table(frame: pd.DataFrame, selected: str | None) -> str:
    lines = ["<div class='table-wrap'><table><thead><tr><th>Year / rule</th><th>Accepted</th><th>Valid</th>"
             "<th>Mean MAE pts</th><th>Mean MFE pts</th><th>MAE / σ</th><th>MFE / σ</th>"
             "<th>Excursion score</th><th>Δ vs base</th><th>95% week interval for Δ</th><th>Terminal +</th></tr></thead><tbody>"]
    for year in (2025, 2026):
        for rule in ("unfiltered", selected) if selected else ("unfiltered",):
            row = frame.loc[(frame.year == year) & (frame.rule == rule)].iloc[0]
            label = f"{year}{' YTD' if year == 2026 else ''} · {LABELS[rule]}"
            interval = ("—" if pd.isna(row.score_delta_ci_low) else
                        f"[{row.score_delta_ci_low:+.2f}, {row.score_delta_ci_high:+.2f}]")
            lines.append(f"<tr class='{'selected' if rule == selected else ''}'><td>{html.escape(label)}</td>"
                         f"<td>{int(row.accepted_signals):,}</td><td>{int(row.valid_n):,}</td>"
                         f"<td>{f(row.mean_mae_points)}</td><td>{f(row.mean_mfe_points)}</td>"
                         f"<td>{f(row.mean_mae_sigma)}</td><td>{f(row.mean_mfe_sigma)}</td>"
                         f"<td>{f(row.mean_clipped_score,3)}</td><td>{f(row.score_delta_vs_unfiltered,3)}</td>"
                         f"<td>{interval}</td><td>{f(100*row.terminal_positive_rate,1)}%</td></tr>")
    return "".join(lines) + "</tbody></table></div>"


def candidate_table(frame: pd.DataFrame, year: int, selected: str | None, eligible: set[str]) -> str:
    lines = ["<div class='table-wrap'><table><thead><tr><th>Rule</th><th>Raw</th><th>Accepted</th><th>Valid</th>"
             "<th>Mean MAE / σ</th><th>Mean MFE / σ</th><th>Score</th><th>Δ vs base</th>"
             "<th>95% week interval for Δ</th><th>Terminal +</th></tr></thead><tbody>"]
    for rule in LABELS:
        row = frame.loc[(frame.year == year) & (frame.rule == rule)].iloc[0]
        annotation = " · selected" if rule == selected else " · eligible" if year == 2025 and rule in eligible else ""
        interval = ("—" if pd.isna(row.score_delta_ci_low) else
                    f"[{row.score_delta_ci_low:+.2f}, {row.score_delta_ci_high:+.2f}]")
        lines.append(f"<tr class='{'selected' if rule == selected else ''}'><td>{html.escape(LABELS[rule]+annotation)}</td>"
                     f"<td>{int(row.raw_candidates):,}</td><td>{int(row.accepted_signals):,}</td>"
                     f"<td>{int(row.valid_n):,}</td><td>{f(row.mean_mae_sigma)}</td>"
                     f"<td>{f(row.mean_mfe_sigma)}</td><td>{f(row.mean_clipped_score,3)}</td>"
                     f"<td>{f(row.score_delta_vs_unfiltered,3)}</td><td>{interval}</td>"
                     f"<td>{f(100*row.terminal_positive_rate,1)}%</td></tr>")
    return "".join(lines) + "</tbody></table></div>"


def sensitivity_table(frame: pd.DataFrame, year: int, selected: str) -> str:
    rows = frame.loc[(frame.year == year) & (frame.rule == selected)].sort_values(["cooldown", "horizon"])
    lines = ["<div class='table-wrap'><table><thead><tr><th>Cooldown</th><th>Horizon</th><th>Valid</th>"
             "<th>Mean MAE pts</th><th>Mean MFE pts</th><th>MAE / σ</th><th>MFE / σ</th>"
             "<th>Score</th><th>Δ vs base</th></tr></thead><tbody>"]
    for r in rows.itertuples():
        lines.append(f"<tr><td>{r.cooldown}</td><td>{r.horizon}</td><td>{r.valid_n:,}</td>"
                     f"<td>{f(r.mean_mae_points)}</td><td>{f(r.mean_mfe_points)}</td>"
                     f"<td>{f(r.mean_mae_sigma)}</td><td>{f(r.mean_mfe_sigma)}</td>"
                     f"<td>{f(r.mean_clipped_score,3)}</td><td class='{'good' if r.score_delta_vs_unfiltered > 0 else 'bad'}'>"
                     f"{f(r.score_delta_vs_unfiltered,3)}</td></tr>")
    return "".join(lines) + "</tbody></table></div>"


def _render(stage: Path) -> None:
    primary = pd.read_csv(stage / "tables/primary.csv")
    sensitivity = pd.read_csv(stage / "tables/sensitivity.csv")
    decision = json.loads((stage / "decision.json").read_text())
    selected = decision["selected_rule"]
    if len(primary) != 20 or set(primary.year) != {2025, 2026}:
        raise ValueError("incomplete saved primary table")
    if selected is None:
        raise ValueError("this renderer expects a qualified selected rule")
    base25 = primary.loc[(primary.year == 2025) & (primary.rule == "unfiltered")].iloc[0]
    base26 = primary.loc[(primary.year == 2026) & (primary.rule == "unfiltered")].iloc[0]
    pick25 = primary.loc[(primary.year == 2025) & (primary.rule == selected)].iloc[0]
    pick26 = primary.loc[(primary.year == 2026) & (primary.rule == selected)].iloc[0]
    positive_sensitivity = int(((sensitivity.rule == selected) & (sensitivity.year == 2026) &
                                 (sensitivity.score_delta_vs_unfiltered > 0)).sum())
    source_run = "20260925T223721Z_gc_ema_excursions_v1"
    report = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GC lower-band long · 2025–2026 filter check</title><style>{CSS}</style></head><body><main>
<header><div class="eyebrow">Abacus / Sahadeva / Study 13</div><h1>Can a close inside the candle’s upper half improve this GC long setup?</h1>
<p class="lead">A simple filter selected on 2025 lower-band signals carried a better descriptive MAE/MFE balance into 2026 YTD. The improvement is uncertain and does not demonstrate a tradable edge.</p>
<div class="badges"><span class="badge">GC 5-minute</span><span class="badge">2025 development · 2026 YTD check</span><span class="badge">10-bar cooldown · 20-bar primary horizon</span><span class="badge">Static offline report</span></div></header>
<section class="grid"><div class="card"><small>Selected condition</small><strong>Upper half</strong><span>Signal close ≥ candle midpoint</span></div>
<div class="card"><small>2025 score improvement</small><strong>{pick25.score_delta_vs_unfiltered:+.3f}σ</strong><span>{int(pick25.valid_n)} valid paths; 95% interval {pick25.score_delta_ci_low:+.2f} to {pick25.score_delta_ci_high:+.2f}</span></div>
<div class="card"><small>2026 score improvement</small><strong>{pick26.score_delta_vs_unfiltered:+.3f}σ</strong><span>{int(pick26.valid_n)} valid paths; 95% interval {pick26.score_delta_ci_low:+.2f} to {pick26.score_delta_ci_high:+.2f}</span></div>
<div class="card"><small>2026 sensitivity</small><strong>{positive_sensitivity}/35</strong><span>Cooldown/horizon cells with positive score difference</span></div></section>
<section class="panel"><h2>The exact rule and comparison</h2>
<div class="formula">base signal: completed close ≤ EMA225 − 3 × residual sigma<br>filter: (close − low) / (high − low) ≥ 0.5<br>entry: next complete 5-minute bar’s unadjusted open</div>
<p>The high, low, and close of the signal candle are all known when it closes. The condition requires a positive candle range. Filtered-out candidates do not start the 10-bar cooldown. The primary measurement uses 20 subsequent five-minute bars and excludes incomplete, gapped, or cross-contract paths.</p>
{compare_table(primary, selected)}
<p class="note">The score is the mean of capped MFE/σ minus capped MAE/σ, with each side capped at 10σ. “Δ vs base” compares this rule with unfiltered lower-band signals in the same year. MAE and MFE are separate extrema, so the score is a path descriptor, not profit.</p></section>
<section class="panel"><h2>What improved, and what did not</h2>
<div class="split"><div><h3>2025 selection</h3><p>Among nine frozen filters, the upper-half close had the best qualifying 2025 score. Mean MAE fell from {base25.mean_mae_points:.2f} to {pick25.mean_mae_points:.2f} GC points; mean MFE moved from {base25.mean_mfe_points:.2f} to {pick25.mean_mfe_points:.2f}. The filtered group had {int(pick25.valid_n)} valid paths versus {int(base25.valid_n)} unfiltered.</p></div>
<div><h3>2026 chronological check</h3><p>Mean MAE moved from {base26.mean_mae_points:.2f} to {pick26.mean_mae_points:.2f} points, while mean MFE moved from {base26.mean_mfe_points:.2f} to {pick26.mean_mfe_points:.2f}. The normalized score improved from {base26.mean_clipped_score:+.3f}σ to {pick26.mean_clipped_score:+.3f}σ, but remained negative. Its week-bootstrap difference interval [{pick26.score_delta_ci_low:+.2f}, {pick26.score_delta_ci_high:+.2f}] crosses zero.</p></div></div>
<div class="callout">This is a directional improvement in the prespecified descriptive score. The interval is broad, and the 2026 results from the earlier unfiltered study had already been viewed. The filter is a candidate for further testing, not an execution recommendation.</div></section>
<section class="panel"><h2>All frozen filters</h2><p>Every tested candidate is retained below. “Eligible” in 2025 means the rule met the fixed support, lower-MAE, MFE-retention, and positive-score gates. The selected rule was chosen only from 2025 rows.</p>
<h3>2025 · selection year</h3>{candidate_table(primary, 2025, selected, set(decision['eligible_training_rules']))}
<h3>2026 YTD · chronological check</h3>{candidate_table(primary, 2026, selected, set())}</section>
<section class="panel"><h2>Cooldown and horizon sensitivity</h2><p>The filter’s score difference is positive in {positive_sensitivity} of 35 requested 2026 cooldown/horizon cells; longer 100-bar horizons are weaker. These are overlapping, correlated views of the same signals and were not used to choose the rule.</p>
<details open><summary>2026 YTD · all 35 cells</summary>{sensitivity_table(sensitivity, 2026, selected)}</details>
<details><summary>2025 · all 35 cells</summary>{sensitivity_table(sensitivity, 2025, selected)}</details></section>
<section class="panel"><h2>Method and limits</h2><ul>
<li>Only 2025 and 2026 YTD signal outcomes were analyzed. The published EMA and sigma retain older chart history needed for warm-up. The 2026 source ends September 18.</li>
<li>Nine simple filters and fixed thresholds were declared after a feature-only support check. The 2025 selection is still exploratory. The 2026 check is chronological but not untouched because its unfiltered results were already known.</li>
<li>Confidence intervals resample ISO weeks jointly for each filter and unfiltered cohort. They are approximate, ignore the nine-candidate search, and should not be read as a calibrated probability of edge.</li>
<li>Filtered signals are re-cooled before outcomes are summarized. Excluded paths remain unavailable rather than zero. The underlying continuous chart is a final backward-adjusted snapshot and may differ from TradingView.</li>
<li>There is no stop, target, fill sequence, transaction cost, spread, slippage, position overlap rule, or realized P&amp;L. Five-minute OHLC cannot establish whether an adverse or favorable extreme occurred first.</li></ul></section>
<footer>Source: pinned GC five-minute and EMA-band releases plus the sealed <a href="../../12_gc_ema_band_excursions/{source_run}/report.md">study 12 run</a>. This report renders only saved study 13 tables. Full candidate evidence and provenance accompany the run.</footer>
</main></body></html>"""
    (stage / "report.html").write_text(report)
    lines = ["# GC lower-band long: two-year filter selection", "",
             "Study 13, protocol 1.0.0. This is a conditional path study, not realized trading performance.", "",
             "## Selected rule", "",
             "Require the completed outer-lower-band signal candle to close in the upper half of its own high–low range. Reapply the 10-bar cooldown after filtering; enter at the next complete five-minute bar's unadjusted open.", "",
             "| Year | Rule | Accepted | Valid | Mean MAE pts | Mean MFE pts | MAE/σ | MFE/σ | Capped score | Δ vs base | 95% week interval for Δ |",
             "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for year in (2025, 2026):
        for rule in ("unfiltered", selected):
            row = primary.loc[(primary.year == year) & (primary.rule == rule)].iloc[0]
            interval = "—" if pd.isna(row.score_delta_ci_low) else f"[{row.score_delta_ci_low:+.2f}, {row.score_delta_ci_high:+.2f}]"
            lines.append(f"| {year}{' YTD' if year==2026 else ''} | {LABELS[rule]} | {int(row.accepted_signals)} | {int(row.valid_n)} | {row.mean_mae_points:.2f} | {row.mean_mfe_points:.2f} | {row.mean_mae_sigma:.2f} | {row.mean_mfe_sigma:.2f} | {row.mean_clipped_score:+.3f} | {f(row.score_delta_vs_unfiltered,3)} | {interval} |")
    lines += ["", "## Interpretation", "",
              f"The 2025-selected rule improved the prespecified score by {pick25.score_delta_vs_unfiltered:+.3f}σ in 2025 and {pick26.score_delta_vs_unfiltered:+.3f}σ in 2026 YTD. The 2026 filtered score itself was {pick26.mean_clipped_score:+.3f}σ, and its difference interval includes zero. This is a weak directional filter candidate, not evidence of net profitability.", "",
              f"The same 2026 rule has a positive score difference in {positive_sensitivity} of 35 cooldown/horizon sensitivity cells, but those cells are correlated and longer horizons weaken. All nine primary candidate filters and full sensitivity values are saved in `tables/primary.csv` and `tables/sensitivity.csv`.", "",
              "2026 was a chronological check, not a pristine holdout: the earlier study had already displayed its unfiltered outcomes. The final adjusted chart snapshot is retrospective, five-minute bars do not resolve high/low ordering, and costs and executable exits are absent.\n"]
    (stage / "report.md").write_text("\n".join(lines))
    (stage / "advice.md").write_text("# Dated interpretation — 2026-09-25\n\n"
        f"Upper-half signal closes were the best eligible 2025 filter and improved the prespecified descriptive score in 2026 YTD by {pick26.score_delta_vs_unfiltered:+.3f}σ. "
        f"The 2026 score remains {pick26.mean_clipped_score:+.3f}σ and the approximate interval for the improvement crosses zero. "
        "Keep the filter as an uncertain research candidate; do not promote it to live execution or a profitability claim. "
        "A later study should freeze the exact filtered signal, specify a realistic stop/target and costs, resolve ordering with finer data, and evaluate on genuinely later unseen dates. "
        "Retain the failures of the other eight prespecified filters in the primary table.\n")


def render(stage: Path) -> None:
    study = Path(__file__).resolve().parent
    run_phase(study.parents[1], study.name, stage, "rendering",
              lambda: _render(stage.absolute()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    render(args.stage)


if __name__ == "__main__":
    main()
