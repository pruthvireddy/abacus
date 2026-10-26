# Future TradingView chart-display specification

This is a specification only. No Pine indicator was created or modified.

## Visual hierarchy

- Draw day (Globex) VWAP and the currently active Asia, London, or NY VWAP as the two main evolving curves. Suppress a local curve outside its published membership or before maturity.
- Draw at most two active frozen destination levels. A/B uses checkpoint-frozen VWAP and the frozen 0.5-sigma extension. C uses event-time frozen day VWAP and session VWAP. Frozen levels must use a different dash style from evolving curves.
- Put labels at the common deadline edge, not indefinitely into the future. Never move a frozen target after forecast creation.

## Compact current-state panel

Show product, anchor/session, forecast timestamp, deadline, elapsed episode/event time, current distance, target distances in ticks/points/sigma, support, and the product-specific outcome vector. A shows frozen-return, no-return, and separately evolving-only contact. B and C show all four mutually exclusive classes, including neither and ambiguous. Percentages must sum to the displayed cohort definition, not to an edited winner-only subset.

Label the estimate `event-time` at departure/corridor creation and `updated conditional` at later ten-minute checkpoints. The update must identify its smaller still-at-risk denominator and original deadline. Historical event-time values remain frozen in replay; later updates append records rather than rewriting them.

## State transitions

- `ACTIVE`: forecast created from completed, available bars; targets and deadline visible.
- `REACHED — DAY/RETURN/EXTENSION/SESSION`: first destination and first-event time retained; fade the reached line but do not replace the original percentage.
- `AMBIGUOUS`: both destinations touched in one one-minute bar; show neither as winner.
- `EXPIRED — NEITHER`: deadline passed with neither destination.
- `UNAVAILABLE`: immature anchor, missing context/path, contract change, clock gap, insufficient horizon, or sparse estimator support. Show the reason, not 0%.

## Hover details

Each probability exposes population, condition, future event, horizon, numerator/denominator, distinct episodes/events, product-sessions, shared weeks, 95% interval, geometry baseline, Brier comparison, chronological rates, release/version, and history cutoff. A hover names frozen versus causal-evolving contact. B hover lists both unequal distances. C hover lists corridor position, width, orientation, session, and the eight-tick/0.25-day-sigma gate.

Do not show an augmented-context value when its development cell has fewer than 100 observations; fall back visibly to the geometry baseline. Before anchor age 30 minutes, suppress all estimates. Before anchor age 60 minutes, path/slope context is unavailable and cannot be inferred from later history.

## Historical examples

The mechanically selected retrospective examples are `figures/chart-example-success.svg`, `figures/chart-example-failure.svg`, and `figures/chart-example-unresolved.svg`. They illustrate reached, failed/reclaimed, and unresolved/ambiguous handling using actual computed targets and paths. They are not curated trade examples and contain no invented percentages.

## Research and replay integrity

Persist forecast timestamp, deadline, frozen prices, outcome vector, support/interval/baseline, model version, and eventual state. Evolving curves may continue to update causally, but prior forecasts and frozen targets must never be recalculated from later bars or backward-adjustment changes. Mark all current historical overlays `RETROSPECTIVE`; these dates are exploratory and the estimates are conditional event frequencies, not trade win rates.
