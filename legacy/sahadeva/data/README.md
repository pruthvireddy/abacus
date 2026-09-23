# ATAS Range XV data

This directory contains enhanced CSV versions of the seven 540-day-window ATAS
Range XV exports. The OHLC values and original row order are preserved exactly.

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
| `bar_start_timestamp` | The source timestamp normalized to ISO `YYYY-MM-DD HH:MM:SS`; interpreted as candle opening time. |
| `bar_completion_timestamp_proxy` | The next bar's opening timestamp when the next bar is in the same 18:00-based session. This is a proxy, not the exact last-trade/completion time. |
| `bar_duration_seconds_proxy` | Difference between the current and next bar-start timestamps, in whole seconds. |
| `completion_proxy_status` | Describes whether and how the completion proxy is usable. |
| `session_date_proxy` | Session date inferred by assigning timestamps at or after 18:00 to the following date. |
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

The exports also do not encode timezone or the chart's configured trading
session. Confirm those ATAS settings before making timezone-specific claims.

## Audit and reproducibility

`range_xv_exports_manifest.json` records the source/enhanced filename mapping,
SHA-256 hashes, row counts, session counts, timestamp ranges, and completion
status counts. `analysis/enhance_range_xv_exports.py` contains the streaming
transformation used to produce these files.

Official references:

- https://docs.atas.net/en/classATAS_1_1Indicators_1_1IndicatorCandle.html
- https://docs.atas.net/en/classATAS_1_1Indicators_1_1ExoticCandleSeriesTimeFrame.html
- https://help.atas.net/en/support/solutions/articles/72000602350
