# Fade the previous-RTH POC approach

Strategy `nq_prev_rth_poc_fade` · Status: weak exploratory evidence · Decision date: 2026-09-29

NQ one-minute Asia window, 20:00–00:00 New York. Use the fixed POC of the last
completed 09:30–16:00 RTH profile. On the first in-window approach from above,
touch POC ±1 tick and enter long at the next contiguous open; from below,
enter short. This side mapping is the study's explicit working interpretation
of “fade,” not a separately confirmed instruction. The previous-RTH profile
was already complete and visible before the signal candle.

## Evidence

The exploratory [1.1.0 run](../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/report.html)
stores [5/10/20-bar metrics](../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/tables/metrics.csv)
and a [candidate/exclusion funnel](../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/tables/funnel.csv).
In the previously inspected 2024–2025 years, 20-bar mean signed close delta
was −1.72 points for 48 long entries (two-week interval −6.33 to +3.37) and
−0.54 points for 46 shorts (−6.08 to +4.51). Both intervals span zero. The
2026 YTD signs differ by side; this is not a stable two-sided finding.
The strict combined-reference quality gate yields no complete horizons before
2018. Prices are hypothetical next opens and one-minute OHLC paths; bid/ask,
slippage, fill probability and net costs are untested.

## Current research advice

Keep this as an exploratory idea, not a trading recommendation. Test whether
a separately specified rejection close or approach-distance condition changes
the pattern on genuinely new data, then model executable fills and costs.

## Decision history

- 2026-09-29: Added after the [original three-setup Asia VP run](../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html) was inspected; no untouched validation set remains in the current history.
