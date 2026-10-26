# Bounce on the first VWAP retest

Strategy `vwap_first_retest_bounce` · **weak evidence** · Last recorded decision: 2026-09-23

Does the first causal return to VWAP lead to movement back toward the approach side?

## Proposed setup and statistics

First touch of the previously known VWAP ±1 tick after 10 minutes on one side and a qualifying departure. Measure outcomes after the touching bar.

**Primary statistic:** Probability of a 0.5 frozen signal-sigma bounce before an equal adverse move within 30 minutes, from the next open.

**Supporting statistics:** Bounce size; penetration; time to movement thresholds; first versus later retests; confirmation-subset counts.

**Comparison:** Later retests and near-VWAP approaches matched on observable context; comparisons are observational.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. The executed definitions are in [protocol 1.0.0](../studies/05_session_vwap/protocol-1.0.0.md); [candidate 4 of the original plan](../studies/05_session_vwap/plan.md) is historical context.

## Evidence and current advice

The [reference run](../runs/05_session_vwap/20260923T015900Z_vwap3/report.html) found favorable-first 0.5σ movement after the observable touch in 61,689 of 132,202 evaluable retests (46.7%; 95% interval 46.2%–47.2%). Adverse-first occurred in 62,010, with 7,017 neither and 1,486 order-ambiguous. The approach-side close confirmation subset was 46.6%, similar to all touches. Matched near approaches show no stable lift; the final-period contrast is −0.2 points at the primary barrier and −2.6 points at a common 8-tick barrier. First retests trail later retests by 3.8 points in the final period. [Scorecards](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/scorecards.csv) · [Subsets](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/subsets.csv) · [Baselines](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/baselines.csv).

The first-touch bounce and simple touch-close confirmation do not merit execution promotion on this evidence. Control overlap and broad segment comparisons remain observational. [Dated run advice](../runs/05_session_vwap/20260923T015900Z_vwap3/advice.md) records supporting and opposing findings.

The [exploratory A/C context run](../runs/05_session_vwap/20260923T035300Z_ac_context/report.html) measured completed-close excursion before the first touch. After a 2σ+ peak, favorable-first bounce was 45.6% in 55,673 events, versus 47.8% after a 1.5–2σ peak in 34,233; fixed 8-tick outcomes clustered near 40–41% across peak bins. A faster return from a 2σ+ peak looked better at the primary barrier but reversed slightly at 8 ticks. The shape cuts do not establish an incremental touch edge over comparable near approaches. [All cuts](../runs/05_session_vwap/20260923T035300Z_ac_context/tables/cuts.csv) · [interactions](../runs/05_session_vwap/20260923T035300Z_ac_context/tables/interactions.csv) · [dated advice](../runs/05_session_vwap/20260923T035300Z_ac_context/advice.md).

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.
- 2026-09-22: evaluated price paths in `20260923T015900Z_vwap3`; no consistent incremental bounce effect was found.
- 2026-09-23: explored pre-touch distance and return shape in `20260923T035300Z_ac_context`; larger excursions and faster returns did not provide a stable improvement across barriers.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
