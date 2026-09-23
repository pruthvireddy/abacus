# Bounce on the first VWAP retest

Strategy `vwap_first_retest_bounce` · **proposed** · Last recorded decision: 2026-09-22

Does the first causal return to VWAP lead to movement back toward the approach side?

## Proposed setup and statistics

First touch of the previously known VWAP ±1 tick after 10 minutes on one side and a qualifying departure. Measure outcomes after the touching bar.

**Primary statistic:** Probability of a 0.5 frozen signal-sigma bounce before an equal adverse move within 30 minutes, from the next open.

**Supporting statistics:** Bounce size; penetration; time to movement thresholds; first versus later retests; confirmation-subset counts.

**Comparison:** Later retests and near-VWAP approaches matched on observable context; comparisons are observational.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. Definitions, thresholds, episode resets, causal timing, ambiguity bounds, and sample rules are in [candidate 4 of the study plan](../studies/05_session_vwap/plan.md). The plan remains the authoritative protocol proposal.

## Evidence and current advice

No strategy outcomes have been computed for this candidate. Supporting runs: none. Opposing runs: none. Evidence strength is unassessed, and execution costs are unspecified. The current research action is to investigate the prespecified price-path statistics and baseline comparisons. A move completed inside the touching bar cannot be credited as attainable after the touch is observed.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
