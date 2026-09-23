# Return to VWAP after departure

Strategy `vwap_return_after_departure` · **proposed** · Last recorded decision: 2026-09-22

How often does a meaningful departure return during its observation window?

## Proposed setup and statistics

First completed close at least 1σ and 4 ticks from mature VWAP after window start. One primary departure per window.

**Primary statistic:** Frozen departure-time VWAP return by window end, conditional on departure, with evolving-VWAP contact reported separately.

**Supporting statistics:** Eligible windows; departures; 10/30/60-minute returns; non-returners; extension; repeated cycles.

**Comparison:** Compare departures at similar elapsed times and distances; keep no-departure windows visible.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. Definitions, thresholds, episode resets, causal timing, ambiguity bounds, and sample rules are in [candidate 3 of the study plan](../studies/05_session_vwap/plan.md). The plan remains the authoritative protocol proposal.

## Evidence and current advice

No strategy outcomes have been computed for this candidate. Supporting runs: none. Opposing runs: none. Evidence strength is unassessed, and execution costs are unspecified. The current research action is to investigate the prespecified price-path statistics and baseline comparisons. A session return percentage is behavioral evidence; an entry and adverse exit still need definition.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
