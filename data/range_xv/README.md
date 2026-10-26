# ATAS Range XV data

This directory contains seven shorter-history enhanced ATAS Range XV CSVs and a
seven-file long-history snapshot under `20191101_20260924/`. The enhanced CSVs
are the canonical analysis-ready files. Their OHLC values, source timestamps,
and original row order are preserved exactly.

On 2026-09-24 the enhanced timestamps were normalized to New York wall time
**at their existing paths**. The export clock appears to use fixed UTC−04:00:
observed winter sessions began at 19:00 in the export while summer sessions
began at 18:00. Interpreting that clock as fixed UTC−04:00 and converting to
`America/New_York` makes both begin at 18:00 Eastern. This is a strong
data-based inference, not a verified ATAS configuration. The five-column raw
exports in `20191101_20260924/source/` remain unchanged as provenance.

## Filename convention

`<contract>_rangexv_<setting>t_<first-session-date>_<last-session-date>.csv`

The Range XV setting is expressed in exchange ticks. For example,
`ESU6_rangexv_5t_20240814_20260908.csv` is the ESU6-labelled Range XV export
with a 5-tick setting and session-date coverage from 2024-08-14 through
2026-09-08.

## Columns

| Column | Meaning |
|---|---|
| `source_row` | One-based row number in the original ATAS export. |
| `source_timestamp` | Original timestamp preserved verbatim in ATAS's `YYYY-DD-MM HH:MM:SS` export format. |
| `bar_start_timestamp` | Candle opening time in New York wall time, `YYYY-MM-DD HH:MM:SS`, converted from the inferred fixed UTC−04:00 export clock. |
| `bar_completion_timestamp_proxy` | The next bar's New York opening time when the next bar is in the same 18:00 Eastern session. This is a proxy, not the exact last-trade/completion time. |
| `bar_duration_seconds_proxy` | Difference between the current and next bar-start timestamps, in whole seconds. |
| `completion_proxy_status` | Describes whether and how the completion proxy is usable. |
| `session_date_proxy` | Session date inferred by assigning New York timestamps at or after 18:00 to the following date. |
| `open`, `high`, `low`, `close` | Original ATAS OHLC values preserved verbatim. |

## Completion-proxy statuses

- `next_bar_start_proxy`: the next same-session bar starts at a later recorded second.
- `next_bar_start_same_second`: multiple Range XV bars opened within the
  same exported second. Row order is known, but sub-second timing and exact
  duration are not.
- `unavailable_session_boundary`: the next row belongs to another inferred
  session, so no completion proxy is assigned across the daily break or weekend.
- `unavailable_export_end`: the final row has no following bar and may have been
  forming when the export was made.

## Interpretation limits

ATAS documents `IndicatorCandle.Time` as candle opening time and
`IndicatorCandle.LastTime` as the time of the candle's last trade. These exports
contain only one timestamp, so `bar_start_timestamp` uses the documented opening
time interpretation. The files do not contain `LastTime`; therefore exact bar
completion cannot be recovered after the fact.

Range XV is event-driven rather than time-driven. The next bar can appear in the
same second during fast activity, or hours later during a quiet period. Treat the
duration field as a timing proxy and do not describe it as exact candle duration.
The exact Range XV construction algorithm is proprietary to ATAS.

The exports do not encode timezone or the chart's configured trading session.
Confirm those ATAS settings before treating the inferred conversion as proven.
Clock normalization changes timestamp labels and derived durations, but does
not create bars missing from an export.

## Audit and reproducibility

The two `range_xv_exports_manifest.json` files record source/enhanced filename
mapping, current SHA-256 hashes, row counts, session counts, timestamp ranges,
and completion status counts. The [clock migration record](../../docs/migration/range-xv-clock-normalization-20260924.json)
records hashes before and after the correction; the
[normalizer](../../scripts/normalize-range-xv-clock.py) records its logic.
Run `python3 scripts/normalize-range-xv-clock.py verify` from the workspace
root to check both current manifests, all fourteen enhanced hashes, retained
long-history source hashes, and compatibility links.
Older sealed studies retain their original input hashes and results. Their
old clock can be reconstructed from the preserved `source_timestamp` and OHLC
columns; they should not be rerun against the corrected files under the old
run ID.
`legacy/sahadeva/data/` CSV links and its manifest resolve to these canonical
files. Historical ATAS settings remain unverified.

Official references:

- https://docs.atas.net/en/classATAS_1_1Indicators_1_1IndicatorCandle.html
- https://docs.atas.net/en/classATAS_1_1Indicators_1_1ExoticCandleSeriesTimeFrame.html
- https://help.atas.net/en/support/solutions/articles/72000602350
- https://help.atas.net/en/support/solutions/articles/72000602490-time-zones-time-zone-configuration-
- https://www.cmegroup.com/trading/metals/files/fact-card-gold-futures-options.pdf
- https://www.cmegroup.com/notices/ser/2022/03/SER-8963.pdf
