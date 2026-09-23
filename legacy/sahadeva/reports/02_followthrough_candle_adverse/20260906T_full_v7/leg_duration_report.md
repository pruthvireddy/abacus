# Reversal-leg duration

Run `20260906T_full_v7`. This report covers ES 4/5/6, GC 6/10, and NQ 10/20 from the seven available filename-labeled Range XV exports.

## Definition

A leg starts with the reversal candle. That candle is position 1. Every immediately following candle with the same `sign(close-open)` direction remains in the leg. The leg ends at the last same-direction candle before the next opposite candle. Dojis break runs under the frozen study definition.

The analysis below keeps completed legs with at least three candles including the reversal (`T ≥ 3`). Legs that reach a provisional export-date boundary before another opposite candle are censored and excluded, not assigned a duration of zero. Duration is the raw timestamp difference from the reversal candle to the final same-direction candle.

## Overall duration of completed three-or-more-candle legs

| Chart | Completed legs | Legs with ≥3 candles | Share | Mean duration proxy (95% date-block CI) | Median | p90 | Mean candles |
|---|---:|---:|---:|---:|---:|---:|---:|
| ES R4 | 16,700 | 8,095 | 48.47% | 5.47 min (4.81–6.29) | 2.15 min | 13.92 min | 4.83 |
| ES R5 | 11,469 | 5,558 | 48.46% | 7.83 min (6.93–9.03) | 3.25 min | 20.63 min | 4.82 |
| ES R6 | 8,353 | 3,957 | 47.37% | 10.72 min (9.46–12.30) | 4.52 min | 27.95 min | 4.85 |
| GC R6 | 46,948 | 23,430 | 49.91% | 2.10 min (1.92–2.28) | 1.13 min | 5.03 min | 4.97 |
| GC R10 | 20,531 | 10,281 | 50.08% | 4.74 min (4.31–5.18) | 2.62 min | 11.52 min | 4.98 |
| NQ R10 | 128,349 | 64,583 | 50.32% | 0.77 min (0.69–0.87) | 0.30 min | 1.90 min | 4.97 |
| NQ R20 | 38,839 | 19,501 | 50.21% | 2.49 min (2.22–2.86) | 0.97 min | 6.23 min | 4.93 |

The mean is the requested average. Median and p90 show skew: a smaller number of slow legs can lift the mean. Mean confidence intervals use 2,000 export-date block bootstrap replicates.

## Session duration breakdown

Sessions are assigned using the reversal candle's raw timestamp. The configured intervals are half-open; Asia crosses midnight. They are raw export-clock proxies, not verified ET sessions, because the files contain no timezone metadata.

| Chart | Session (raw clock) | T≥3 legs | Mean minutes (95% block CI) | Median | p90 | Mean candles | T≥3 share |
|---|---|---:|---:|---:|---:|---:|---:|
| ES R4 | Asia (18:00–03:00) | 1,381 | 11.51 (10.02–13.18) | 6.68 | 27.23 | 4.96 | 46.73% |
| ES R4 | New York AM (09:30–12:00) | 2,919 | 1.82 (1.57–2.14) | 1.00 | 3.95 | 4.83 | 49.03% |
| ES R4 | New York PM (12:00–16:00) | 1,922 | 4.15 (3.24–5.39) | 2.21 | 9.62 | 4.85 | 48.56% |
| ES R5 | Asia (18:00–03:00) | 965 | 15.85 (13.73–18.22) | 9.48 | 34.99 | 4.92 | 48.15% |
| ES R5 | New York AM (09:30–12:00) | 1,990 | 2.77 (2.35–3.31) | 1.52 | 6.07 | 4.81 | 48.61% |
| ES R5 | New York PM (12:00–16:00) | 1,341 | 5.81 (4.50–7.68) | 2.98 | 14.48 | 4.83 | 49.16% |
| ES R6 | Asia (18:00–03:00) | 675 | 20.88 (18.37–24.33) | 13.30 | 47.50 | 4.92 | 47.24% |
| ES R6 | New York AM (09:30–12:00) | 1,413 | 3.83 (3.28–4.52) | 2.18 | 8.58 | 4.89 | 47.43% |
| ES R6 | New York PM (12:00–16:00) | 980 | 8.26 (6.39–10.85) | 4.42 | 19.89 | 4.82 | 49.32% |
| GC R6 | Asia (18:00–03:00) | 7,841 | 2.43 (2.23–2.65) | 1.47 | 5.55 | 4.99 | 50.46% |
| GC R6 | New York AM (09:30–12:00) | 5,214 | 1.04 (0.91–1.17) | 0.67 | 2.33 | 4.97 | 49.67% |
| GC R6 | New York PM (12:00–16:00) | 3,419 | 2.48 (1.79–3.47) | 1.23 | 6.62 | 4.97 | 50.07% |
| GC R10 | Asia (18:00–03:00) | 3,509 | 5.30 (4.84–5.81) | 3.35 | 12.25 | 4.96 | 50.63% |
| GC R10 | New York AM (09:30–12:00) | 2,258 | 2.43 (2.11–2.79) | 1.62 | 5.24 | 5.04 | 50.17% |
| GC R10 | New York PM (12:00–16:00) | 1,498 | 5.96 (4.07–8.51) | 3.12 | 15.05 | 5.00 | 50.54% |
| NQ R10 | Asia (18:00–03:00) | 13,477 | 1.44 (1.28–1.63) | 0.82 | 3.23 | 5.03 | 50.65% |
| NQ R10 | New York AM (09:30–12:00) | 25,448 | 0.21 (0.19–0.24) | 0.12 | 0.47 | 4.97 | 50.19% |
| NQ R10 | New York PM (12:00–16:00) | 13,045 | 0.63 (0.52–0.79) | 0.35 | 1.50 | 4.92 | 50.45% |
| NQ R20 | Asia (18:00–03:00) | 4,250 | 4.45 (3.91–5.12) | 2.50 | 10.07 | 4.97 | 50.88% |
| NQ R20 | New York AM (09:30–12:00) | 7,663 | 0.71 (0.63–0.82) | 0.40 | 1.53 | 4.93 | 50.62% |
| NQ R20 | New York PM (12:00–16:00) | 3,679 | 2.21 (1.76–2.83) | 1.18 | 5.04 | 4.93 | 49.07% |

## Longest average duration by reversal time

The table reports the top three supported 30-minute windows per chart. A supported window has at least 100 qualifying legs across at least 10 export dates.

| Chart | Rank | Reversal raw-clock window | Legs ≥3 | Mean duration proxy (95% CI) | Median | p90 | Mean candles |
|---|---:|---|---:|---:|---:|---:|---:|
| ES R4 | 1 | 21:00–21:30 | 104 | 10.97 min (8.63–13.90) | 6.34 | 23.70 | 4.91 |
| ES R4 | 2 | 07:00–07:30 | 109 | 10.50 min (8.22–13.77) | 5.80 | 24.16 | 4.93 |
| ES R4 | 3 | 18:00–18:30 | 208 | 9.87 min (7.08–13.71) | 2.48 | 29.58 | 4.99 |
| ES R5 | 1 | 20:00–20:30 | 110 | 14.08 min (10.40–19.05) | 6.91 | 30.64 | 5.18 |
| ES R5 | 2 | 18:00–18:30 | 155 | 13.37 min (9.18–19.04) | 3.03 | 36.95 | 4.98 |
| ES R5 | 3 | 04:00–04:30 | 102 | 10.89 min (8.12–14.74) | 7.46 | 21.04 | 5.12 |
| ES R6 | 1 | 18:00–18:30 | 118 | 16.89 min (12.01–23.50) | 5.41 | 49.13 | 5.00 |
| ES R6 | 2 | 08:30–09:00 | 128 | 10.48 min (7.65–14.81) | 3.74 | 32.38 | 5.06 |
| ES R6 | 3 | 13:00–13:30 | 107 | 9.86 min (7.63–13.02) | 6.13 | 21.18 | 4.55 |
| GC R6 | 1 | 16:00–16:30 | 192 | 6.50 min (4.95–8.60) | 3.90 | 16.18 | 4.87 |
| GC R6 | 2 | 00:30–01:00 | 202 | 5.05 min (4.31–5.91) | 3.38 | 11.65 | 4.84 |
| GC R6 | 3 | 19:00–19:30 | 247 | 4.89 min (4.09–5.88) | 3.02 | 11.15 | 5.09 |
| GC R10 | 1 | 06:30–07:00 | 101 | 10.69 min (8.93–12.70) | 9.18 | 22.37 | 4.81 |
| GC R10 | 2 | 19:00–19:30 | 107 | 10.18 min (7.93–12.98) | 5.85 | 20.93 | 5.12 |
| GC R10 | 3 | 06:00–06:30 | 115 | 9.01 min (7.42–11.12) | 6.10 | 17.79 | 4.79 |
| NQ R10 | 1 | 16:30–17:00 | 425 | 4.17 min (2.76–6.72) | 0.73 | 6.59 | 4.93 |
| NQ R10 | 2 | 18:30–19:00 | 450 | 2.24 min (1.82–2.80) | 1.15 | 5.83 | 4.95 |
| NQ R10 | 3 | 05:30–06:00 | 479 | 2.22 min (1.91–2.58) | 1.50 | 5.18 | 4.90 |
| NQ R20 | 1 | 16:30–17:00 | 133 | 8.57 min (5.21–15.18) | 1.82 | 17.64 | 4.44 |
| NQ R20 | 2 | 18:30–19:00 | 144 | 7.28 min (5.36–9.79) | 3.87 | 14.95 | 4.78 |
| NQ R20 | 3 | 00:00–00:30 | 157 | 7.17 min (5.50–9.39) | 4.25 | 15.47 | 5.03 |

## Morning versus 22:00 example

| Chart | Reversal window | Legs ≥3 | Mean duration proxy | Median | p90 | Mean candles |
|---|---|---:|---:|---:|---:|---:|
| ES R4 | 09:30–10:00 | 875 | 1.18 min | 0.78 | 2.61 | 4.86 |
| ES R4 | 22:00–22:30 | 76 | 11.60 min | 7.90 | 25.63 | 4.79 |
| ES R5 | 09:30–10:00 | 590 | 1.74 min | 1.16 | 3.85 | 4.86 |
| ES R5 | 22:00–22:30 | 47 | 14.54 min | 9.32 | 28.47 | 4.49 |
| ES R6 | 09:30–10:00 | 428 | 2.51 min | 1.61 | 4.92 | 4.97 |
| ES R6 | 22:00–22:30 | 33 | 19.58 min | 14.05 | 38.84 | 5.03 |
| GC R6 | 09:30–10:00 | 1,447 | 0.75 min | 0.53 | 1.65 | 4.94 |
| GC R6 | 22:00–22:30 | 485 | 2.26 min | 1.58 | 4.83 | 4.89 |
| GC R10 | 09:30–10:00 | 623 | 1.75 min | 1.32 | 3.75 | 5.01 |
| GC R10 | 22:00–22:30 | 214 | 4.59 min | 3.59 | 9.71 | 4.86 |
| NQ R10 | 09:30–10:00 | 9,072 | 0.12 min | 0.08 | 0.25 | 4.96 |
| NQ R10 | 22:00–22:30 | 785 | 1.43 min | 0.92 | 3.13 | 5.04 |
| NQ R20 | 09:30–10:00 | 2,686 | 0.40 min | 0.27 | 0.87 | 4.95 |
| NQ R20 | 22:00–22:30 | 255 | 4.56 min | 2.63 | 9.12 | 4.91 |

## Interpretation limits

The exact result is the number of consecutive same-direction range candles. Clock values are raw timestamp-difference proxies. The files do not identify timezone or whether timestamps mark bar opens or closes. Repeated timestamps are retained, so some completed legs have zero recorded duration. No intrabar duration is invented.

These are same-color candle legs, not guaranteed profitable price paths. Open gaps and wick movement can differ from candle direction.

## Outputs

- [All 30-minute windows](tables/leg_duration_by_reversal_30min.csv)
- [Overall chart summary](tables/leg_duration_summary.csv)
- [Session duration breakdown](tables/leg_duration_by_session.csv)
- [Time-window rankings](tables/leg_duration_rankings_30min.csv)
- [Independent real-event reconciliation](tables/leg_duration_manual_reconciliation.csv)
- [Time-of-day figure](figures/leg_duration_30min.svg)
- [Methodology](methodology.md)
- [Run manifest](run_manifest.json)
