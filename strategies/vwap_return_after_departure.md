# Return to VWAP after departure

Strategy `vwap_return_after_departure` · **descriptive evidence** · Last recorded decision: 2026-09-24

How often does a meaningful departure return during its observation window?

## Proposed setup and statistics

First completed close at least 1σ and 4 ticks from mature VWAP after window start. One primary departure per window.

**Primary statistic:** Frozen departure-time VWAP return by window end, conditional on departure, with evolving-VWAP contact reported separately.

**Supporting statistics:** Eligible windows; departures; 10/30/60-minute returns; non-returners; extension; repeated cycles.

**Comparison:** Compare departures at similar elapsed times and distances; keep no-departure windows visible.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. The executed definitions are in [protocol 1.0.0](../studies/05_session_vwap/protocol-1.0.0.md); [candidate 3 of the original plan](../studies/05_session_vwap/plan.md) is historical context.

## Evidence and current advice

The [reference run](../runs/05_session_vwap/20260923T015900Z_vwap3/report.html) found frozen VWAP contact by window end after 33,327 of 42,487 first departures (78.4%; 95% shared-date interval 77.7%–79.2%) across 3,039 eligible product-days and correlated views. Evolving VWAP contact occurred after 38,325 departures. Only 18,757 of 42,466 30-minute-capable departures contacted the frozen level within 30 minutes (44.2%), and 9,160 never returned by window end. The primary pooled rate fell from 79.9% in development to 75.9% in the final period. Supporting evidence: [scorecards](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/scorecards.csv), [horizons](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/horizons.csv). Limiting evidence: [breakdowns](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/breakdowns.csv), [paths](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/paths.csv).

This is evidence of frequent reversion with strong deadline dependence, not a trade win rate or an incremental edge. Retain it as a context and timing hypothesis; define entry, adverse exit, fill, overlap, and cost rules before execution research. [Dated run advice](../runs/05_session_vwap/20260923T015900Z_vwap3/advice.md) records the complete interpretation.

The later [conditional-probability run](../runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/report.html) measured the remaining risk set directly at regular checkpoints. Among 489,835 outcome-capable two-minute checkpoints from 55,623 fresh episodes, product-specific frozen-return probability within the next 30 minutes was 22.0% for ES, 20.5% for NQ, and 19.8% for GC. Rates varied sharply with current distance and elapsed survival. Evolving-only contact added roughly 1.8%–2.0%, confirming that reference movement can change the answer.

In the paired return-versus-0.5-sigma-extension race, return was first in only 15.4%–17.1%, but the barriers were deliberately unequal: median return distance was about 1.18–1.26 sigma versus about 0.50–0.52 sigma to extension. Neither resolved in 37.0%–42.1%. Consequently this is a destination-probability display candidate, not an execution comparison with a 50% neutral benchmark. Added elapsed/path context improved chronological Brier error only 0.5% for return and 1.0% for the competing race, with specific-context coverage below 15%; prefer geometry/clock estimates by default. [Run advice](../runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/advice.md) records the full chart decision.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.
- 2026-09-22: evaluated price paths in `20260923T015900Z_vwap3`; classified as descriptive evidence only, with no profitability claim.
- 2026-09-24: measured surviving-episode checkpoints and competing frozen barriers in `20260924T155331Z_vwap11`; retained sparse chart-oriented probabilities, with the small added-context improvement and unequal geometry disclosed.

[Original study](../studies/05_session_vwap/README.md) · [Conditional study](../studies/11_vwap_conditional_probabilities/README.md) · [Research library](../reports/index.html)
