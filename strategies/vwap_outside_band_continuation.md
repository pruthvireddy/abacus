# Sustained outside-band continuation

Strategy `vwap_outside_band_continuation` · **proposed** · Last recorded decision: 2026-09-22

Does a known period of outside closes distinguish persistence from reversion?

## Proposed setup and statistics

A fresh outside-2σ episode whose completed closes stay beyond the same band for 10 further minutes. Signal only when persistence is observable.

**Primary statistic:** Continuation and fade symmetric-barrier outcomes from the identical confirmation time and entry reference.

**Supporting statistics:** Persistence frequency; movement before confirmation; further extension; re-entry and VWAP return; observable slope and agreement.

**Comparison:** Paired mirror directions at the same confirmation; failed-persistence comparisons require a common landmark.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. Definitions, thresholds, episode resets, causal timing, ambiguity bounds, and sample rules are in [candidate 6 of the study plan](../studies/05_session_vwap/plan.md). The plan remains the authoritative protocol proposal.

## Evidence and current advice

No strategy outcomes have been computed for this candidate. Supporting runs: none. Opposing runs: none. Evidence strength is unassessed, and execution costs are unspecified. The current research action is to investigate the prespecified price-path statistics and baseline comparisons. Future trend-day labels cannot select the signal, and paired directions are not independent evidence.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
