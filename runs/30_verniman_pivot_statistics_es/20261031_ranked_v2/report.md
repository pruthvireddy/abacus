# Verniman Pivot Statistics — ES

Requested calendar: 2020-01-01–2026-10-30. Actual eligible sample: 2020-01-03–2026-09-18; 875 days. Repository-only descriptive research; no purchases or external data extension.

## Price breaks and actual EMA6 crossings

The first distinction is whether EMA6 actually crosses the pivot, was already aligned, or remains opposite when price closes through it. An eventual return without a new EMA crossing is a later path label; compare its measured penetration rather than assuming that label was known at the break.

| condition | condition_value | events | days | returned_without_new_cross | actual_confirmed | return_censored | mean_penetration_points |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all | all | 4059 | 695 | 1989 | 1837 | 695 | 13.578 |
| ema_state_at_cross | already_aligned | 1114 | 512 | 914 | 0 | 200 | 13.116 |
| ema_state_at_cross | opposite | 2478 | 669 | 1075 | 1370 | 400 | 13.054 |
| ema_state_at_cross | same_close_actual_crossing | 467 | 281 | 0 | 467 | 95 | 17.464 |
| initial_confirmation_state | already_aligned | 1114 | 512 | 914 | 0 | 200 | 13.116 |
| initial_confirmation_state | initially_unconfirmed | 2478 | 669 | 1075 | 1370 | 400 | 13.054 |
| initial_confirmation_state | same_close_actual_crossing | 467 | 281 | 0 | 467 | 95 | 17.464 |
| confirmation_kind | delayed | 1370 | 577 | 0 | 1370 | 367 | 21.057 |
| confirmation_kind | same_close | 467 | 281 | 0 | 467 | 95 | 17.464 |
| confirmation_kind | unknown | 2222 | 519 | 1989 | 0 | 233 | 8.150 |

Return censoring means the price episode did not reverse before the observed endpoint. A return-censored episode may already have an actual EMA confirmation; return censoring and confirmation censoring are different and their counts can overlap.

## Primary 30-minute price-path baseline

| denominator | valid_days | unknown | mean_points | median_points | positive_rate | mean_ci95_low | mean_ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3830 | 686 | 229 | 0.037 | 0 | 0.496 | -0.215 | 0.303 |

| condition_value | denominator | valid_days | mean_points | positive_rate | mean_favorable_points | mean_adverse_points |
| --- | --- | --- | --- | --- | --- | --- |
| already_aligned | 1057 | 500 | -0.448 | 0.482 | 8.284 | 8.667 |
| opposite | 2332 | 659 | 0.296 | 0.503 | 9.022 | 8.287 |
| same_close_actual_crossing | 441 | 274 | -0.167 | 0.490 | 9.074 | 9.050 |

These conditional differences are exploratory. A result near zero, a broad interval, sparse support or a weaker recent/calendar slice is retained as negative or inconclusive evidence, not removed from the report. No classification is promoted to a tradable edge by this report.

## Recurrence and repetition

| metric | denominator | estimate | median | p90 | zero_share | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- | --- | --- |
| price_crosses | 875 | 4.639 | 3 | 11 | 0.206 | 4.320 | 4.948 |
| ema_crosses | 875 | 2.155 | 1 | 5 | 0.269 | 2.006 | 2.302 |
| touch_bars | 875 | 10.229 | 7 | 24 | 0.147 | 9.586 | 10.848 |

All raw crosses are retained. First-per-day and first-per-section panels are saved alongside them; repeated events on the same day are not independent sessions.

## Calendar, indicators and retests

Saved tables include every calendar year/month, month of year and trailing 20/60/120 eligible observed sessions at the requested cutoff. Opening states, cloud/VWAP conditions, fixed 15/30/60-minute horizons, section/day endpoints, EMA-cross retests and section transitions retain explicit support and unknown counts. Curated web controls select saved rows only.

## Methods and limits

- Repository-retained ES data only; requested coverage ends 2026-10-30, while retained market data ends 2026-09-18. Missing dates/contracts and retrospective full-day eligibility limit generalization.
- Historical pivot available_at remains unverified. Nominal 09:25 timing does not establish a historically executable pre-open signal.
- Returned-without-EMA and eventual confirmation labels are known later. Already-aligned EMA6 is distinct from an actual new line crossing.
- Signed displacement and excursions describe price paths. No entries, fills, costs or net profitability are tested. Broad slices are exploratory.
- Five-minute EMA20/50 and three-minute EMA6 use full-session same-contract closes, with 250 preceding valid native bars. Globex VWAP uses one-minute HLC3/volume and resets at 18:00 New York.
- Price/EMA events are strict side changes on completed three-minute closes. Equality retains the previous strict side; the opening state is not a cross. Section membership follows bar open, while information arrives at close.
- Fixed horizons require complete RTH paths. Signal-bar earlier highs/lows are excluded; late/unknown outcomes remain null. Retests use subsequent three-minute bars and do not infer intrabar order.
- Overall mean and primary 30-minute mean/positive-rate intervals use 2,000 non-circular moving-block replicates of five observed sessions, seed 20261031. Whole-day records retain dependence among repeated events. Intervals do not correct source selection or multiple exploration.
- Fewer than 30 distinct days is a sparse cell. Sampled close occupancy is not exact time above/below a line. Point/basis-point changes are not realized P&L.

Reproduce from the retained settings/input/source/environment freeze and exact run commands. Numerical verification, source-cell transfer integrity and website checks are separate evidence.
