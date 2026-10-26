# Fade after re-entry inside 2σ

Strategy `vwap_reentry_fade` · **exploratory evidence** · Last recorded decision: 2026-09-23

Does visible rejection improve the opportunity enough to justify waiting?

## Setup and statistics

First completed re-entry inside 2σ, linked to the original outside episode; next-open reference.

**Primary statistic:** The same 30-minute symmetric-barrier probability after re-entry, alongside a paired policy comparison over all original outside episodes.

**Supporting statistics:** Confirmation rate; no-confirmation frequency; movement missed; adverse extension avoided; remaining VWAP distance.

**Comparison:** Immediate fade and waiting policy compared over all initial episodes with one shared deadline.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. Definitions, thresholds, episode resets, causal timing, ambiguity bounds, and sample rules are in [candidate 2 of the study plan](../studies/05_session_vwap/plan.md). [Protocol 1.1.0](../studies/05_session_vwap/protocol-1.1.0.md) fixes the exploratory re-entry calculation.

## Evidence and current advice

The [exploratory context run](../runs/05_session_vwap/20260923T035300Z_ac_context/report.html) found that 89,475 of 90,938 original A episodes (98.4%) published a first re-entry inside the same 2σ band. Only 84,997 retained a full 30-minute follow-up; among those, 38,909 (45.8%) reached the favorable half-sigma barrier first. Another 1,463 never re-entered, and 4,470 re-entered too late for the full horizon. [Re-entry counts and outcomes](../runs/05_session_vwap/20260923T035300Z_ac_context/tables/reentry.csv) · [dated advice](../runs/05_session_vwap/20260923T035300Z_ac_context/advice.md).

This is partial evidence. The later-signal conditional rate is not a paired policy comparison against fading immediately over all A episodes. The current research action is to compare both policies with a shared deadline and account for missed opportunities, execution assumptions, and costs. Conditioning only on episodes that confirm would hide missed opportunities.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.
- 2026-09-23: evaluated confirmation and conditional post-re-entry paths in `20260923T035300Z_ac_context`; a paired waiting-policy comparison remains open, so no execution claim was made.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
