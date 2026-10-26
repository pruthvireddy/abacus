"""Render saved tables into offline reports and figures only."""
from __future__ import annotations
from pathlib import Path
import html
import json
import numpy as np
import pandas as pd


def md_table(frame, columns):
    f=frame[columns].copy()
    for k in f:
        if pd.api.types.is_float_dtype(f[k]): f[k]=f[k].map(lambda v:f'{v:.2f}' if pd.notna(v) else '—')
    return '| '+' | '.join(f.columns)+' |\n| '+' | '.join(['---']*len(f.columns))+' |\n'+'\n'.join('| '+' | '.join(str(v) for v in row)+' |' for row in f.itertuples(index=False,name=None))


def render(stage):
    stage=Path(stage)
    config=json.loads((stage/'config.json').read_text())
    if config['primary_timeframe'] != '3m' or config['timeframes'] != ['3m']:
        raise ValueError('Current report requires the corrected 3-minute-only study')
    s=pd.read_csv(stage/'tables/summary.csv')
    y=pd.read_csv(stage/'tables/yearly.csv')
    primary=s.query("timeframe == '3m' and window == 'globex' and cohort == 'common_calendar'")
    overall=primary.query("segmentation == 'all'")
    atr=primary.query("segmentation == 'atr_regime'")
    realized=primary.query("segmentation == 'realized_regime'")
    year=y.query("timeframe == '3m' and window == 'globex' and cohort == 'common_calendar' and segmentation == 'all'")
    cash=s.query("timeframe == '3m' and window == 'us_cash' and cohort == 'common_calendar' and segmentation == 'all'")
    gc_day=s.query("product == 'GC' and timeframe == '3m' and window == 'gc_day' and cohort == 'common_calendar' and segmentation == 'all'")
    matched=s.query("timeframe == '3m' and window == 'globex' and cohort == 'matched_dates' and segmentation == 'all'")
    start,end=config['common_calendar']
    bootstrap=config['bootstrap']
    cols=['product','sessions','mean_crosses','median_crosses','p25_crosses','p75_crosses','p90_crosses','mean_ci95_low','mean_ci95_high']
    lines=['# EMA6 crossings of Globex VWAP','',
      f"Descriptive study, protocol {config['protocol_version']}. Main comparison: {start} through {end}, a 6-period EMA of closing prices on 3-minute bars. Each count is a completed-bar EMA6 crossing of the moving, 18:00 New York anchored VWAP. A touch alone is not a crossing; departure from equality is. Zero-cross sessions remain in the denominator.",'',
      '## Main crossing frequencies','',md_table(overall,cols),'',
      f"Mean intervals are 95% circular moving-block bootstrap intervals ({bootstrap['replicates']:,} resamples; blocks of {bootstrap['block_observed_sessions']} observed sessions). Medians and percentiles describe the distribution of daily counts. Counts are sensitive to timeframe and equality convention.",'',
      '## Prior available ATR14 volatility','',
      'ATR14% is the last completed daily value available at the Globex open, ranked against its preceding 252 daily observations separately for each product. Low/normal/high use fixed thirds. The rank uses complete daily history, not just the selected VWAP sample.','',
      md_table(atr,['product','regime','sessions','mean_crosses','median_crosses','mean_ci95_low','mean_ci95_high']),'',
      '## Realized range relative to prior ATR','',
      'Quiet <0.75 ATR; normal 0.75–<1.25 ATR; active ≥1.25 ATR. This full-session high-low classification is only known after the day; it is different from the background ATR regime.','',
      md_table(realized,['product','regime','sessions','mean_crosses','median_crosses','mean_ci95_low','mean_ci95_high']),'',
      '## Annual comparison','',md_table(year,['product','year','sessions','mean_crosses','median_crosses','p90_crosses','small_cell']),'',
      '2021 and 2026 are partial calendar years. GC coverage is especially sparse and selected. Yearly differences combine changing conditions with changing sample composition.','',
      '## Intraday windows','',
      'The common US window uses bar opens from 09:30 inclusive to 16:00 exclusive New York, exactly aligned to the 3-minute grid. For GC this is not its exchange-specific regular session.','',
      md_table(cash,cols),'',
      'GC-day membership uses bar opens in [08:20,13:30). On the fixed 3-minute grid, the first included bar opens at 08:21 and the last at 13:27, for 309 minutes of bar exposure. The 08:18 bar is excluded even though it overlaps the window boundary.','',
      md_table(gc_day,cols),'',
      '## Matched dates','',
      'The following compares only eligible dates shared by ES, NQ and GC within the common calendar, reducing calendar-composition differences. Selection remains retrospective.','',md_table(matched,cols),'',
      '## Monthly evidence and coverage','',
      '[Calendar-month statistics](tables/monthly.csv), [month-of-year statistics](tables/month_of_year.csv), [annual statistics](tables/yearly.csv), [count distributions](tables/distribution.csv), [daily observations](daily_panel.csv), [crossing events](crossings.csv), and [coverage](tables/coverage.csv) are saved alongside this report. Every table includes denominators. Cells with fewer than 30 sessions are flagged; unobserved months are absent evidence, never zero-cross months.','',
      '## Methods and limits','',
      '- EMA6 uses alpha 2/7 on 3-minute chart-bar closes, continuous through sessions and rolls. It is computed from all observed pinned minute-source history, including days excluded from the VWAP sample; at least 250 preceding bars are required. No missing prices are filled. Evaluated closes are checked against the derived 3-minute bars.',
      '- The 3-minute bars and Globex VWAP are study-local derivations from the pinned one-minute source using Bhishma\'s existing session aggregation. No published 3-minute VWAP release is claimed or created. Session membership retains the original published whole-product-day eligibility audit.',
      '- VWAP uses 3-minute output-bar HLC3 and volume. The EMA and VWAP share the same pinned back-adjusted analytical price basis. Historical absolute prices incorporate later rolls. No execution prices, returns or P&L are analyzed.',
      '- Both moving lines matter: these are EMA/VWAP relation changes, not necessarily price crossings of a fixed level. First Globex bars are undefined, and anchor-reset jumps are excluded. Window membership uses bar open and observations become known at bar close.',
      '- Prior daily ATR comes from a separate TradingView continuous chart. Its session, settlement and roll conventions differ from the intraday source; temporal alignment does not certify historical point-in-time data or native chart parity.',
      '- Eligibility excludes whole days with missing expected minutes, including possible no-trade minutes, and unsupported historical schedules. This creates a selected, uneven sample; results cannot be generalized to all trading days without broader input work.',
      '- All available history, common-calendar, matched-date, direction and opening-30-bar sensitivity results remain in the tables. The common calendar is retained from the original protocol. The user requested this 3-minute revision after the original timeframes were examined. Month-of-year pools years and can be confounded by their mix.',
      '- Bootstrap intervals describe sample uncertainty under short observed-session dependence. They do not account for missing-day selection, source revisions or long-run regime changes. This is descriptive research, not a tested trading rule.',
      '', 'Reproduction: use the frozen source, settings, input lock, environment lock and exact commands in the run manifest. Rendering reads saved tables; verification and integrity have separate receipts.','']
    report='\n'.join(lines)
    (stage/'report.md').write_text(report)
    # Report HTML: render authored Markdown without requiring a new runtime package.
    import re
    parts=[]; in_table=False; in_list=False
    for line in lines:
        for textline in line.splitlines():
            if textline.startswith('|'):
                cells=[html.escape(c.strip()) for c in textline.strip('|').split('|')]
                if all(set(c)<=set('- ') for c in cells): continue
                if not in_table: parts.append('<div class="scroll"><table>');in_table=True
                parts.append('<tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>'); continue
            if in_table: parts.append('</table></div>');in_table=False
            if textline.startswith('- '):
                if not in_list: parts.append('<ul>');in_list=True
                parts.append('<li>'+html.escape(textline[2:])+'</li>');continue
            if in_list: parts.append('</ul>');in_list=False
            if not textline: continue
            escaped=html.escape(textline)
            escaped=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',escaped)
            if textline.startswith('## '): parts.append('<h2>'+escaped[3:]+'</h2>')
            elif textline.startswith('# '): parts.append('<h1>'+escaped[2:]+'</h1>')
            else: parts.append('<p>'+escaped+'</p>')
    if in_table:parts.append('</table></div>')
    if in_list:parts.append('</ul>')
    style='body{max-width:1100px;margin:40px auto;padding:0 22px;color:#183045;background:#f7f8fa;font:16px/1.6 system-ui}h1,h2{line-height:1.25}h2{margin-top:36px}.scroll{overflow-x:auto}table{border-collapse:collapse;background:white;font-size:14px}td{padding:8px 12px;border-bottom:1px solid #dce2e9;white-space:nowrap}tr:first-child{font-weight:bold}a{color:#1269b0}img{width:100%;background:white}'
    figure_html=''.join(f'<img src="figures/{p.name}" alt="{html.escape(p.stem)}">' for p in sorted((stage/'figures').glob('*.png')))
    (stage/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EMA6 crossings of Globex VWAP</title><style>'+style+'</style><body>'+''.join(parts[:3])+figure_html+''.join(parts[3:])+'</body></html>')
    (stage/'advice.md').write_text('# Interpretation — 2026-10-23 — 3-minute EMA6\n\nThis study describes crossing frequency for the corrected 6-period EMA of 3-minute closing prices; it does not establish an entry rule or profitability. Use the yearly/monthly denominators, matched-date cohort and distribution before translating an average into an expectation for one day. Prior ATR regime is available before the session; eventual range/ATR is known after the session. Uneven, retrospective input eligibility limits generalization. The 3-minute VWAP is a study-local derivation from pinned minute inputs. Any execution strategy or broader data-eligibility study requires a new protocol and run.\n')
    metrics={'schema_version':1,'study_id':'28_globex_ema_crossings','metric':'completed_bar_ema6_globex_vwap_crosses_per_session',
       'units':'crosses/session','horizon':'one Globex session','primary_cohort':'common_calendar',
       'primary_timeframe':'3m','ema_period':6,'ema_price':'close',
       'protocol_version':config['protocol_version'],
       'vwap_derivation':'Study-local 3-minute HLC3/volume VWAP from pinned minute source; original published session eligibility retained; no 3-minute feature release.',
       'rows':overall.replace({np.nan:None}).to_dict('records'),
       'uncertainty':f"95% circular observed-session moving-block bootstrap; {bootstrap['replicates']} replicates, block {bootstrap['block_observed_sessions']}",
       'missing_and_exclusions':'tables/coverage.csv and input_audit.csv','source':'tables/summary.csv'}
    (stage/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')

