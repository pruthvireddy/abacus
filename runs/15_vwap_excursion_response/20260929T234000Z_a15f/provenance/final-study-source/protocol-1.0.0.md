# Executable protocol 1.0.0

The complete proposed [plan](plan.md) is adopted for this run, subject only to the
explicit pre-outcome clarifications below. The plan's exact hash, this protocol,
machine settings, numerical source and synthetic tests are frozen in
`freeze.json`. The feature-only pilot completed before freezing. No real forward
MAE/MFE, return-rate or first-move summaries were inspected before this freeze.

## Pre-outcome clarifications

- `contains_roll` can flag a session-opening mapping transition. The pilot found
  an ES instance on 2021-12-13 at the 18:00 anchor, with one contract in both source
  minutes and throughout the day. Do not discard a valid day on that flag alone.
  Require exact product/date/raw-symbol/instrument/roll joins, a stable adjustment,
  and continuous identities across each event and measured path. There is no
  measurement across an actual contract or adjustment change.
- All reference contact comparisons use integer price ticks. Convert feature
  levels into raw contract coordinates before half-up rounding. An evolving zone
  at minute open uses only the last completed two-minute bar. Its center remains
  fixed for that minute. The first anchor candle has no prior reference.
- Whole-zone reference overtake means the completed reference update moves the
  entire rounded +/-1-tick zone past the current close in the excursion's
  direction: `d*(close-old_center)>1` and `d*(close-new_center)<-1` in ticks. Mere
  zone overlap after an update is not recorded as a traded touch; an actual
  later source-range overlap is required. This explicit whole-zone definition
  avoids treating a rounding-edge adjustment as traded price movement.
- Within a minute, a gap crossing known at its open precedes an observed range
  contact. A parent that gaps through is terminated even if that minute later
  contacts VWAP; module 2 still records that contact. Contact inside the minute
  precedes a reference update at its close. Within a completed two-minute candle,
  terminations precede threshold signals. No new parent starts in its terminating
  candle. Touch timestamps are minute intervals; confirmation is the containing
  two-minute close, and response starts at the next open.
- A signal at the final session close has no next in-session entry and is
  retained as an excluded candidate. Earlier signals retain every horizon row,
  including unavailable boundary outcomes. Module 1/2 windows continue beyond
  parent termination. Module 3 can admit first contacts after 50 departure candles.
- The primary response direction is continuation for departures and bounce for
  touches; its sign is the original departure side. The opposite is fade or
  through. Reports explicitly name long/short for each side. MAE/MFE is full-path
  excursion from next open, never an executable limit fill or realized P&L.
- For the >=30-minute sensitivity, departure anchor age is used for both modules,
  including touch responses; touch-age and return-latency marginal summaries are
  separately descriptive. Main context cuts use the primary 2-sigma cohort,
  mirrored sides, and one context variable at a time.
- Shared week draws use the union of feature-eligible session-date ISO weeks
  across products. The saved 2,000 multinomial count vectors with seed 1501 are
  identical for all cells. Empty bootstrap denominators are omitted and counted.
  Marginal percentile intervals are descriptive, not simultaneous inference.
  The evolving-minus-frozen contrast is paired within event and week. Different
  threshold clocks are not paired entry comparisons.
- Zero/all-success cells retain 0/n or n/n and their bootstrap values, explicitly
  flagging unresolved boundary uncertainty. No-event cells contain null estimates.
  Missing touch sigma affects sigma-scaled/barrier outcomes, not otherwise valid
  point/tick response. All horizon probabilities use complete-path denominators.
- The year sample is the complete locked release: ES/NQ 2021–2026 and GC
  2016–2026 where eligible. 2026 ends September 18, not a full calendar year.
  Coverage reports include excluded earlier candidate days from the release audit.
- Fixed example selection: lexicographically earliest stable horizon ID at
  10 candles in each product/session for departure return, departure non-return,
  touch bounce-first, through-first, ambiguous, and earliest excluded departure
  horizon. An empty class is disclosed. Examples are illustrations, not an
  optimized sample; actual source minutes and lagged references are saved.
- The existing workspace environment is used with `uv --locked --no-sync`.
  Automatic synchronization attempted a package build requiring unavailable
  network access. No dependency or package source changes are needed; installed
  versions, Python version and the unchanged workspace lock are saved.

## Outputs and verification

Produce six linked ledgers: parent, threshold, touch, candidate, departure-horizon,
and touch-horizon. Stable event IDs encode product/session/date/bar and threshold;
all forward columns are explicitly outcomes. Save Parquet plus compressed CSV
ledgers outside ordinary Git on sealing, with hashes and a retained locator.
Save wide summary and coverage tables in CSV/Parquet; the report schema is pinned.

Main scopes are per-horizon eligible, common complete-50 cohort, and >=30-minute
sensitivity. Main results separate products, sessions, sides and thresholds,
with mirrored-side descriptive totals. Year/period and marginal context tables
are stability diagnostics. Required means, quantiles, denominators, support flags,
probabilities and shared-week intervals follow the plan. Figures derive solely
from saved summary/example tables.

Synthetic tests cover the declared causal and path rules. The independent audit
recounts deterministic examples from raw one-minute inputs without invoking the
measurement implementation, checks keys, denominators, monotonicity, symmetry,
barrier class counts, source availability and summary-to-ledger reconciliation.
No run is sealed until the audit, report inspection, documentation and navigation
checks pass. A rendering or audit implementation can be added after freezing;
it must read saved outcomes and cannot alter the frozen numerical executable.
Any numerical correction requires an explicit amendment and a new execution ID.

True aggressor volume delta is unavailable. This is price-based descriptive
research on retrospectively eligible, previously inspected history. It does not
establish profitability, independent replications, or a deployable trading rule.
No external publication, indicator, orders or deployment are authorized.
