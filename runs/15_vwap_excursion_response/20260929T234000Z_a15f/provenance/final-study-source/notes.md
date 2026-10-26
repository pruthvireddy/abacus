# Planning decisions

## 2026 September 29

The user requested a fresh plan and a copyable implementation prompt for three
anchored-VWAP questions: post-band-close MAE/MFE and close behavior, probability
of returning to VWAP, and post-return bounce/fade behavior. The requested output
separates Asia, London, New York and optionally the full Globex day; the plan
includes all four. The current turn is planning only. No new research code,
outcome computation or indicator work is authorized for this planning turn.

Study 15 was unused when this directory was created. The handoff prompt gives
the receiving coding agent explicit implementation/execution instructions.
Existing study 05/06/11 evidence is preserved, not deleted or relabeled.

Working assumptions pending any user clarification: delta means price change;
both bounce toward the original excursion side and continuation through VWAP
are measured. The user mentioned 15 candles before repeating 5/10/20/50, so
15 is retained as a supplementary horizon. ES/NQ/GC inherit the requested
existing-study context, with products kept separate.

Proposed methodological choices are explicit in [the plan](plan.md): first
crossing per threshold per VWAP-separated parent, next-open measurements,
session-contained complete horizons, evolving VWAP primary and frozen VWAP
secondary, both directional responses, and a symmetric 0.5-touch-sigma race.
Early valid signals are included; the old 30-minute warm-up is only a declared
sensitivity. These are proposed defaults, not numerical findings.

Read-only catalog inspection verified that the feature release uses completed
output-bar HLC3 and population sigma, its local session windows end before the
anchor calculations do, and OHLCV has no true aggressor-volume delta. Existing
input manifest pins are retained in the new study lock; full partition
verification is assigned to the implementation agent before outcomes.

No protocol is marked frozen, no reference run is selected, and there are no
new computed outcomes. Planning verification consists of documentation/link
checks, metadata/input-pin consistency and a regenerated research index.

## 2026 September 29 Chart companion request

The user subsequently supplied a GC MAE/MFE Pine indicator and explicitly asked
for its display style and cooldown statistics on top of the VWAP OE indicator,
for the one rule of fading a two-minute close outside an anchored VWAP's two-sigma
band. This authorizes the [chart companion](pine/README.md), independently of
executing the three-module historical study. The old planning scope above is a
record of the earlier request, not a prohibition on this later authorized work.

The new companion measures longs below the lower band and shorts above the
upper band from the next contiguous open. It defaults to every outside close,
with optional fresh crossings, and maintains five independent cooldown cohorts.
This follows the pasted chart-study convention rather than claiming to implement
the broader plan's parent-excursion logic. The original OE's Asia 20:00–00:00
and London 03:00–08:00 inputs are retained; users may choose wider windows.
Both original sources are preserved in `pine/`; new script/provenance and
numerical helper tests live with this study. No saved run or result table was
modified. No external script was uploaded or published.

Local helper tests passed; Pine Editor compilation and visual replay are not
verified. The study remains planned and has no selected reference run.

## 2026 September 29 Chart rendering correction

The user supplied a TradingView screenshot reporting RE10140 (74 plot counts,
limit 64) and accepted drawing only the last two days of VWAPs while retaining
historical buy/sell markers. The editable companion now draws the latest two
observed daily occurrences of each anchor using bounded polylines, removes the
invisible gradient fills, and leaves markers and statistics across loaded
history. Weekend gaps do not count as observed sessions. The statistical engine
is unchanged. Local helper and rendering-queue checks passed; native acceptance
of this revision still needs TradingView verification. Existing sources and
sealed evidence remain unchanged.
