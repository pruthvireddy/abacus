# Implementation decisions

2026-10-06: The user's pasted specification authorizes implementation of the
indicator and synthetic validation. It does not authorize a market-data study.
Confirmed-pivot anchors and one next-open entry convention implement that scope.

Combined means the union of retained long and short records; the memory input
is per side, so Combined has up to twice the configured capacity. This follows
the requested per-bucket/per-direction rolling storage.

Pre-exit extrema are bounded on intrabar exit candles and exact on open exits.
Ordering uncertainty and confidence intervals are separate concepts. Ambiguity
does not become a guessed loss, guessed win, or omitted denominator row.

Entry distance is direction-signed distance to the nearest unexpanded zone
boundary, zero inside the zone, divided by frozen ATR. It is retained for future
analysis but does not filter or retrospectively select this version's events.

The minimum completed sample affects emphasis only. No outcome-based ranking or
composite opportunity score is introduced.

The artifact is a source prototype: TradingView compilation, chart execution,
alerts, and visual performance are explicitly unverified. An optional Pine
self-check switch and local tests exercise the production numerical helpers.
No study navigation metadata or public bundle is created by this source task.
