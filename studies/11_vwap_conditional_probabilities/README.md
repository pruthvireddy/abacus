# VWAP conditional probabilities

Study `11_vwap_conditional_probabilities` · ES / NQ / GC · completed exploratory research

This study estimates three chart-oriented conditional price-path probabilities:

1. remaining probability of returning to VWAP after a fresh departure has survived;
2. frozen VWAP return versus a further frozen-sigma extension; and
3. frozen day-VWAP versus active-session-VWAP first passage after a completed-close session-VWAP failure.

The primary calculation uses the pinned two-minute `session_anchored_vwap__1.0.0`
release and matching unadjusted one-minute paths. The independently calculated
five-minute release is a correlated sensitivity. Globex VWAP is the day VWAP;
Asia, London, and NY are the only local-session VWAPs. All published dates are
exploratory because earlier VWAP outcomes were already inspected.

[Plan](plan.md) · [Frozen protocol](protocol-1.0.0.md) · [Decision notes](notes.md) · [Input lock](inputs.lock.json) · [Reference report](../../runs/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/report.html)

## Chart presentation prototype

The [Pine v6 stats-only export, revision 4](../../reports/exports/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/20260925T034500Z_stats_only_v4/README.md) presents a compact historical-statistics panel without chart VWAP/band/target plots or the original OE/TICK/footprint logic. Internal VWAP calculations still determine the live chart state; the sealed run is unchanged. Revision 1 hit TradingView's `CE10205` oversized-switch error; revision 2 split the switch but hit `CE10117` total compiled-token limit; revision 3 compacted repeated hover prose. Revision 4 retains the same rates and denominator support in a standalone table-only script. It remains a chart-feed proxy, not a fresh research result. A private TradingView editor compile and replay remain required before chart use.

## Result

The reference run constructed 489,856 primary two-minute departure checkpoints
from 55,635 episodes and 15,078 mature day/session corridor events. Product-level
30-minute frozen-return rates were 19.8%–22.0%; the primary return-versus-extension
race resolved return first in 15.4%–17.1%, extension first in 42.4%–45.9%, and
neither in 37.0%–42.1%. After a session-VWAP failure into the corridor, day VWAP
was reached first in 14.1%–21.2%, while session VWAP was reclaimed first in
74.3%–80.3%.

Geometry, clock, and prior volatility explain most of the usable variation.
Added elapsed/path context reduced evaluation Brier error by only 0.5% for A and
1.0% for B, with supported specific-context coverage of 10.7% and 14.6%. No C
path-context cell cleared the frozen 100-row development floor. These results
support a sparse, deadline-explicit chart display, not a trading or profitability
claim.

## Reproduce

Use a fresh sortable run ID. The feature-only pilot must finish before the frozen
protocol is executed:

```sh
.venv/bin/python studies/11_vwap_conditional_probabilities/pilot.py --run-id <id>
.venv/bin/python studies/11_vwap_conditional_probabilities/run.py --run-id <id> --workers 3
.venv/bin/python studies/11_vwap_conditional_probabilities/summarize.py --run-id <id>
.venv/bin/python studies/11_vwap_conditional_probabilities/render.py --run-id <id>
.venv/bin/python studies/11_vwap_conditional_probabilities/verify.py --run-id <id>
.venv/bin/python studies/11_vwap_conditional_probabilities/seal.py --run-id <id>
```

Never reuse a run ID, alter the published release, or write into an older sealed
run. These are conditional event probabilities, not trading win rates or net
profitability estimates.
