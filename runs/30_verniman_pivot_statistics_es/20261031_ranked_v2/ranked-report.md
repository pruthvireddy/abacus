# Verniman Pivot Statistics — ES: ranked extension

Requested calendar: 2020-01-01–2026-10-30. Retained repository market sessions: 2020-01-01–2026-09-18. No data acquired or release rebuilt.

| Cohort | Eligible sessions | Actual eligible dates |
|---|---:|---|
| pivot_matched_rth | 875 | 2020-01-03–2026-09-18 |
| vwap_only_rth | 1308 | 2020-01-03–2026-09-18 |
| vwap_only_full_globex | 1292 | 2020-01-03–2026-09-18 |

The 20 ranked questions are defined in the retained implementation matrix and protocol 2.0.0. Full saved summaries are in tables/ranked_summary.csv. Public report tables and figures select those cells only. Each summary retains units, numerator, valid denominator, supporting days, missing/censored counts, dates and sparse status.

The pivot-matched cohort is reconciled against the unchanged completed 20261031_repo_v2 baseline. Existing ema_events remain EMA6–pivot events. Actual EMA6–VWAP crossings use contemporaneous completed minute-HLC3/volume VWAP. RTH and Globex state initialization and populations remain explicit.

Forward outcomes are RTH-only with 30 minutes primary and 15/60-minute context. Recent20/60/120 comparisons exclude each recent window from its preceding comparison. Intervals use 2,000 five-session day-block replicates with seed20261031; broad conditional views are exploratory. Historical pivot availability remains unverified and baseline results were viewed before this extension. No fills, costs or profitability are tested.

Independent event/episode/exposure/summary verification, exact publication-cell transfer and local application checks are separate receipts. Read their actual scope and status; coverage alone does not establish validity.
