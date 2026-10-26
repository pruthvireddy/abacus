# Asia session VP — previous-RTH POC fade and VA continuation

Previous-day means the fixed previous RTH 09:30–16:00 New York profile, known before the evening signal. D fades its first in-window POC contact from each approach side; E enters after a VAH/VAL breakout and later confirmed retest. Both enter at the next contiguous one-minute open in 20:00–00:00 New York. A horizon includes its entry candle and requires every one-minute bar through its close by midnight. Average close Δ is side-signed: close minus entry for longs, entry minus close for shorts. MFE and MAE are intrahorizon extrema, not realized profit or loss. TR60 is the mean true range of the 60 complete minutes before the signal candle, not a conventional 14-bar ATR. Undefined TR60 values are omitted only from normalized columns, with denominators saved in tables/metrics.csv. The pictured approach ≥1 ATR condition was not requested as a signal filter and is not applied.

## 2024–2025 descriptive period

| Setup | Side | Bars | N | Avg MFE (pts) | Avg MAE (pts) | Avg close Δ (pts) | Avg MFE (TR60) | Avg MAE (TR60) | Avg close Δ (TR60) | Favorable close |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prev RTH POC fade | Short | 5 | 47 | 7.01 | 9.18 | -1.80 | 1.32 | 1.67 | -0.18 | 46.8% |
| Prev RTH POC fade | Short | 10 | 47 | 9.73 | 11.29 | -1.70 | 1.95 | 2.05 | -0.01 | 40.4% |
| Prev RTH POC fade | Short | 20 | 46 | 13.32 | 15.07 | -0.54 | 2.79 | 2.70 | 0.28 | 52.2% |
| Prev RTH POC fade | Long | 5 | 50 | 5.75 | 8.00 | -1.58 | 1.13 | 1.81 | -0.36 | 46.0% |
| Prev RTH POC fade | Long | 10 | 50 | 7.54 | 10.04 | -1.68 | 1.51 | 2.27 | -0.42 | 38.0% |
| Prev RTH POC fade | Long | 20 | 48 | 11.20 | 14.28 | -1.72 | 2.23 | 3.27 | -0.58 | 47.9% |
| Prev RTH VA retest | Short | 5 | 43 | 8.09 | 7.99 | -0.10 | 1.15 | 1.31 | -0.27 | 46.5% |
| Prev RTH VA retest | Short | 10 | 43 | 11.12 | 11.43 | -0.90 | 1.52 | 1.84 | -0.39 | 37.2% |
| Prev RTH VA retest | Short | 20 | 41 | 14.66 | 17.49 | -6.10 | 2.09 | 2.66 | -0.83 | 41.5% |
| Prev RTH VA retest | Long | 5 | 74 | 5.91 | 5.79 | 0.64 | 1.28 | 1.34 | 0.10 | 40.5% |
| Prev RTH VA retest | Long | 10 | 73 | 8.45 | 7.14 | 1.37 | 1.95 | 1.60 | 0.33 | 49.3% |
| Prev RTH VA retest | Long | 20 | 71 | 12.83 | 10.08 | 3.99 | 2.89 | 2.23 | 0.86 | 57.7% |

## 2026 year to date

| Setup | Side | Bars | N | Avg MFE (pts) | Avg MAE (pts) | Avg close Δ (pts) | Avg MFE (TR60) | Avg MAE (TR60) | Avg close Δ (TR60) | Favorable close |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prev RTH POC fade | Short | 5 | 44 | 13.53 | 16.28 | -4.49 | 1.21 | 1.40 | -0.29 | 38.6% |
| Prev RTH POC fade | Short | 10 | 44 | 17.18 | 22.65 | -6.22 | 1.55 | 2.01 | -0.50 | 45.5% |
| Prev RTH POC fade | Short | 20 | 44 | 29.61 | 30.56 | 3.26 | 2.65 | 2.67 | 0.45 | 52.3% |
| Prev RTH POC fade | Long | 5 | 44 | 14.88 | 17.98 | -1.44 | 1.39 | 1.66 | -0.16 | 52.3% |
| Prev RTH POC fade | Long | 10 | 44 | 19.85 | 23.92 | -3.07 | 1.86 | 2.22 | -0.29 | 50.0% |
| Prev RTH POC fade | Long | 20 | 44 | 26.50 | 33.66 | -7.74 | 2.57 | 3.07 | -0.51 | 47.7% |
| Prev RTH VA retest | Short | 5 | 33 | 11.37 | 21.68 | -7.67 | 0.95 | 1.58 | -0.47 | 36.4% |
| Prev RTH VA retest | Short | 10 | 33 | 22.23 | 27.55 | 2.67 | 1.66 | 2.01 | 0.05 | 48.5% |
| Prev RTH VA retest | Short | 20 | 31 | 33.60 | 38.16 | 3.73 | 2.47 | 2.80 | 0.34 | 48.4% |
| Prev RTH VA retest | Long | 5 | 54 | 11.25 | 12.17 | -0.79 | 1.28 | 1.21 | -0.01 | 44.4% |
| Prev RTH VA retest | Long | 10 | 54 | 15.10 | 16.93 | 0.48 | 1.70 | 1.73 | 0.14 | 51.9% |
| Prev RTH VA retest | Long | 20 | 50 | 20.67 | 24.68 | -1.14 | 2.24 | 2.47 | -0.07 | 58.0% |

## Evidence and limits

These added hypotheses were specified after the earlier Asia VP report was inspected. The 2024–2025 and 2026 samples are therefore descriptive reuse, not untouched validation. The first complete strict-quality horizon occurs in 2018; Reference completeness is conservative: the saved release flags the combined prior-reference set rather than just prior RTH. Retrospective completeness and future-path censoring are reported separately. One-minute OHLCV cannot establish intrabar order, actual fills, costs, or net profitability. The full 2010–2026 evidence and excluded candidates are in the saved tables.

The full-history, year-by-year and exclusion tables are in `tables/`. The earlier three setups remain in the [sealed 1.0.0 report](../../../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html).
