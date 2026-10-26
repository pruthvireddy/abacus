# Continue after a previous-RTH VAH/VAL breakout and retest

Strategy `nq_prev_rth_va_breakout_retest` · Status: mixed exploratory evidence · Decision date: 2026-09-29

NQ one-minute Asia window, 20:00–00:00 New York. Use the fixed VAH and VAL of
the last completed 09:30–16:00 RTH profile. A close at least one tick above
VAH arms a long; a later range touch and close holding at/above VAH within
60 minutes enters long at the next contiguous open. Mirror the rule below VAL
for shorts. Breakouts may originate after 18:00. The previous-RTH level is
known before each signal candle.

## Evidence

The exploratory [1.1.0 run](../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/report.html)
stores [5/10/20-bar metrics](../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/tables/metrics.csv)
and a [candidate/exclusion funnel](../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/tables/funnel.csv).
In the previously inspected 2024–2025 years, 20-bar mean signed close delta
was +3.99 points for 71 longs (two-week interval −0.11 to +9.53) and −6.10
points for 41 shorts (−12.39 to −0.97). The 2026 YTD estimates reverse or
weaken those signs: −1.14 for 50 longs and +3.73 for 31 shorts. This is
inconsistent across periods and does not establish a durable edge.
The strict combined-reference quality gate yields no complete horizons before
2018. Prices are hypothetical next opens and one-minute OHLC paths; bid/ask,
slippage, fill probability and net costs are untested.

## Current research advice

Retain for research only. Check why long and short signs shift across years,
then test prespecified rules on genuinely new observations with a fill/cost
model. Do not infer profitability from favorable excursions.

## Decision history

- 2026-09-29: Added after the [original three-setup Asia VP run](../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html) was inspected; no untouched validation set remains in the current history.
