# Fade the first close outside 2σ

Strategy `vwap_extreme_fade` · **proposed** · Last recorded decision: 2026-09-22

Does a fresh extreme close offer useful retracement before further adverse extension?

## Proposed setup and statistics

The first eligible completed close beyond a mature anchor’s 2σ band; trade direction points toward VWAP. One signal per excursion.

**Primary statistic:** Probability of a favorable 0.5 signal-sigma move before an equal adverse move within 30 minutes.

**Supporting statistics:** Episode frequency; frozen and evolving VWAP returns; MFE/MAE; time to retracement; adverse extension.

**Comparison:** Matched 1–2σ departures with comparable time, volatility, and starting distance where overlap permits.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. Definitions, thresholds, episode resets, causal timing, ambiguity bounds, and sample rules are in [candidate 1 of the study plan](../studies/05_session_vwap/plan.md). The plan remains the authoritative protocol proposal.

## Evidence and current advice

No strategy outcomes have been computed for this candidate. Supporting runs: none. Opposing runs: none. Evidence strength is unassessed, and execution costs are unspecified. The current research action is to investigate the prespecified price-path statistics and baseline comparisons. A high eventual-return rate can conceal severe extension before the return.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
