# Fade the first close outside 2σ

Strategy `vwap_extreme_fade` · **weak evidence** · Last recorded decision: 2026-09-23

Does a fresh extreme close offer useful retracement before further adverse extension?

## Proposed setup and statistics

The first eligible completed close beyond a mature anchor’s 2σ band; trade direction points toward VWAP. One signal per excursion.

**Primary statistic:** Probability of a favorable 0.5 signal-sigma move before an equal adverse move within 30 minutes.

**Supporting statistics:** Episode frequency; frozen and evolving VWAP returns; MFE/MAE; time to retracement; adverse extension.

**Comparison:** Matched 1–2σ departures with comparable time, volatility, and starting distance where overlap permits.

Scope: ES, NQ, GC; 2m and 5m; Globex, Asia, London, and NY anchors. Main local-anchor comparisons remain within that anchor’s membership window. The executed definitions are in [protocol 1.0.0](../studies/05_session_vwap/protocol-1.0.0.md); [candidate 1 of the original plan](../studies/05_session_vwap/plan.md) is historical context.

## Evidence and current advice

The [reference run](../runs/05_session_vwap/20260923T015900Z_vwap3/report.html) found favorable-first 0.5σ movement in 40,480 of 86,475 evaluable exits (46.8%; 95% interval 46.2%–47.4%). Adverse-first occurred in 41,390, with 2,677 neither and 1,928 order-ambiguous. The pooled matched 1–2σ comparison is +1.1 percentage points at the primary barrier, but distance support does not overlap and 2024/final intervals include zero. A common fixed 8-tick barrier reverses the pooled contrast (−1.4 points) and is negative in the final period (−3.2 points). The primary rate fell from 47.7% in development to 45.3% in the final period. [Scorecards](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/scorecards.csv) · [Baselines](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/baselines.csv) · [Paths](../runs/05_session_vwap/20260923T015900Z_vwap3/tables/paths.csv).

The bare first outside-2σ fade does not merit execution promotion on this evidence. Treat the baseline contrasts and segment grids as exploratory, with no familywise-adjusted edge claim. [Dated run advice](../runs/05_session_vwap/20260923T015900Z_vwap3/advice.md) records supporting and opposing findings.

The [exploratory A/C context run](../runs/05_session_vwap/20260923T035300Z_ac_context/report.html) examined NY clock time, pre-exit path, ATR, and opening balance. For Globex VWAP in the NY window, first-hour 2σ exits were favorable first in 48.7% of 2,260 cases versus 42.4% of 4,131 later cases at the half-sigma target. At a common 8-tick target the order reversed, 28.5% versus 35.2%. The NY-local VWAP cannot signal during its first 30 minutes under the 30-minute warm-up. The proposed early weakness is therefore unsupported as a stable conditional edge. [NY table](../runs/05_session_vwap/20260923T035300Z_ac_context/tables/ny_early.csv) · [context-matched controls](../runs/05_session_vwap/20260923T035300Z_ac_context/tables/control_comparisons.csv) · [dated advice](../runs/05_session_vwap/20260923T035300Z_ac_context/advice.md).

Any later profitability claim requires unadjusted fill prices, explicit costs, protected evaluation, and exact run/table references. Preserve inconclusive and negative results alongside positive findings.

## Decision history

- 2026-09-22: registered the proposed candidate during repository consolidation. No trading implementation or result was added.
- 2026-09-22: evaluated price paths in `20260923T015900Z_vwap3`; simple fade evidence is weak and deteriorates on a common 8-tick comparison.
- 2026-09-23: explored A context in `20260923T035300Z_ac_context`; NY first-hour weakness was not robust across barrier definitions, so no execution rule was promoted.

[Study](../studies/05_session_vwap/README.md) · [Research library](../reports/index.html)
