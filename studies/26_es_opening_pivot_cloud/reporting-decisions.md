# Reporting decisions fixed before strategy outcomes

These choices implement protocol version 1. They are fixed independently of all
strategy outcomes; no development, validation or test estimates set bin edges.

- Primary estimate is early minus confirmed dollars per input-eligible day for
  mask A and fixed 2R. Genuine no-trade days contribute zero. Unavailable outcomes
  stay null; the full input-eligible primary estimate is undefined if any primary
  outcome is unavailable. Common-defined secondary estimates retain their count
  and qualification. The fixed-2R primary should have no unavailable eligible days.
- All 16 variants retain daily and trade summaries. Early/confirmed comparisons
  use paired daily differences. A separate both-filled comparison is explicitly
  conditional on both fills and therefore omits missed opportunities. Verne exits
  are also compared to 2R on their common defined daily population; coverage
  differences are saved separately.
  The confirmation-fill rate is confirmed-policy fills/common candidates; it
  includes filter, structural, cutoff and target-availability attrition and is
  not presented as a raw confirmation-close event rate.
- Percentile intervals use 4,000 bootstrap resamples and seed 26021. The sampling
  unit is the session; this is day-clustered because there is at most one trade
  per variant/session. The week sensitivity resamples complete observed ISO-week
  clusters, including partial boundary weeks, and divides by resampled day count.
  At least two observed days/weeks are required for the corresponding interval.
- Secondary inferential comparisons are the other fifteen variants against
  early/mask-A/fixed-2R on common defined days. Two-sided bootstrap sign-tail probabilities are reported as
  descriptive bootstrap probabilities; their Holm adjustment spans the fifteen
  comparisons in this family. These are not randomization-test p-values. No cut is promoted to
  an inferential discovery and no tiny cell is ranked.
- Year is labelled partial for 2022 and 2026; splits are development 2022–2024,
  validation 2025 and locked temporal test 2026. Every one-way cut reports trades,
  available sessions, mean trade dollars/R and a fixed-seed bootstrap interval.
  Fewer than 30 trades is flagged as weak descriptive evidence.
  Save pooled, development, validation and temporal-test primary comparisons
  separately. The pooled result is exploratory retrospective evidence.
- Fixed left-closed, right-open continuous bins (the last bin includes infinity):
  pivot-zone width points: 0, 1, 2, 5, 10; pivot/cloud separation points: 0, 1,
  2, 5, 10; cloud width/ATR: 0, 0.25, 0.5, 1, 2; prior-known ATR14 points: 0, 2,
  4, 8, 16; initial stop distance points: 0, 2, 4, 8, 16; absolute entry-to-pivot
  distance points: 0, 1, 2, 5, 10; target distance/R: 0, 0.5, 1, 2, 3, 5.
  A zero-width pivot has its own `single_price` bin; missing values are `unknown`.
  Volatility regime uses the causal completed pre-open ATR14, never a future
  session range. Cloud-width/ATR uses the completed-reaction ratio.
- Five-minute fill bins are 09:35, 09:40, 09:45, 09:50 and 09:55 New York.
  Confirmation delay bins are 0, 1, 2, 3 completed bars or unavailable. Pivot
  type grouping recognizes YVAL, YPOC and HVE case-insensitively, retains sorted
  combinations, labels other nonempty descriptions `other`, and preserves the
  original text in the ledger. Target identity uses original ordinal/description.
- Only two two-way cuts are produced: year × direction and entry policy × mask.
  One-way cuts include all requested categorical and continuous attributes. They
  are correlated descriptive views, not independent replications.
- Equity is chronological, one ES contract, starts at zero, and includes all
  defined days. Maximum drawdown includes the initial zero equity peak. Undefined
  profit factor/payoff ratio stays null when its denominator does not exist.
- Examples are chosen deterministically: earliest date then candidate ID in each
  of win, loss, failed confirmation and structural invalidation. Selection labels
  explicitly disclose absent classes. Charts render saved ledger values and do
  not recompute signals, features or outcomes.
- The inspiration chart date is 2026-09-15 (confirmed by the user before outcome
  execution). Tag it in ledgers and apply the regular eligibility gates. The user
  explicitly declined a date-specific excluding sensitivity. The input audit
  found both a quote-contract mismatch and feature unreadiness on that date, so
  it is ineligible under regular gates. Prior visual exposure qualifies the evaluation
  as retrospective temporal validation, not a pristine prospective trial.
- Narada consumes saved aggregate tables and selected local figures. Up to four
  CSV projections are explicit downloads. Source maps pin source tables and
  exact projection columns; publication source/asset hashes are finalized before
  sealing. No browser code calculates research results.
