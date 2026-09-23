# VWAP cross, acceptance, and retest

Strategy `vwap_cross_acceptance_retest` · **proposed** · Last recorded decision: 2026-09-22

Does accepted price on a new side make VWAP useful support or resistance?

## Proposed setup and statistics

Completed cross, acceptance within 10 minutes, then a held causal retest within 30 minutes. Enter after the confirming bar.

**Primary statistic:** 30-minute symmetric-barrier probability after the held retest, with the complete cross-to-confirmation funnel.

**Supporting statistics:** Acceptance and retest conversion; failures/timeouts; continuation; whipsaws; frozen 1σ/2σ targets.

**Comparison:** Initial-cross entry versus waiting over all crosses, with a common deadline and no-trade cases retained.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. Definitions, thresholds, episode resets, causal timing, ambiguity bounds, and sample rules are in [candidate 5 of the study plan](../studies/05_session_vwap/plan.md). The plan remains the authoritative protocol proposal.

## Evidence and current advice

No strategy outcomes have been computed for this candidate. Supporting runs: none. Opposing runs: none. Evidence strength is unassessed, and execution costs are unspecified. The current research action is to investigate the prespecified price-path statistics and baseline comparisons. A selected held-retest subset does not by itself show improvement over trading the original cross.

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
