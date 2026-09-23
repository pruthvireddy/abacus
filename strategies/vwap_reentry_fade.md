# Fade after re-entry inside 2σ

Strategy `vwap_reentry_fade` · **proposed** · Last recorded decision: 2026-09-22

Does visible rejection improve the opportunity enough to justify waiting?

## Proposed setup and statistics

First completed re-entry inside 2σ, linked to the original outside episode; next-open reference.

**Primary statistic:** The same 30-minute symmetric-barrier probability after re-entry, alongside a paired policy comparison over all original outside episodes.

**Supporting statistics:** Confirmation rate; no-confirmation frequency; movement missed; adverse extension avoided; remaining VWAP distance.

**Comparison:** Immediate fade and waiting policy compared over all initial episodes with one shared deadline.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. Definitions, thresholds, episode resets, causal timing, ambiguity bounds, and sample rules are in [candidate 2 of the study plan](../studies/05_session_vwap/plan.md). The plan remains the authoritative protocol proposal.

## Evidence and current advice

No strategy outcomes have been computed for this candidate. Supporting runs: none. Opposing runs: none. Evidence strength is unassessed, and execution costs are unspecified. The current research action is to investigate the prespecified price-path statistics and baseline comparisons. Conditioning only on episodes that confirm would hide missed opportunities.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
