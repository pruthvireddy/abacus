# Verniman Pivot Levels — frozen experimental contract v1.0.0

Frozen 2026-10-30 before inspecting this indicator's market results. This is a
new user-authorized scope, separate from the completed Phase 1 and Phase 2
records. N1/E1 and the contextual selector are engineering hypotheses; source
method fidelity and profitability are not acceptance criteria.

## Inputs, profiles and availability

Use standard five-minute candles with extended electronic-session bars. All
boundaries are civil `America/New_York` timestamps, including DST. Prices use
the chart symbol and `syminfo.mintick`. The verification contract is
`CME_MINI:ESZ2026`, the actual December 2026 ES contract, with unadjusted prices;
availability and adequate history must be checked in the native chart. No
other timeframe, security request, composite or manual override is used.

Previous RTH is the latest actual observed completed 09:30–16:00 session,
requiring all 78 contiguous five-minute bars and positive total volume. Use
the latest actual observed RTH, Friday for Monday in a normal week; an observed
partial or shortened latest RTH invalidates the reference rather than choosing
an older full session. No exchange-holiday calendar is inferred. A wholly
absent session cannot be distinguished from a closed holiday without one;
record the source RTH date and this first-version coverage limitation. Overnight is the preceding 18:00 through 09:25 prefix, requiring all
185 contiguous five-minute bars, including the terminal 09:20–09:25 bar.

Profile defaults: row width 16 minimum ticks, zero grid origin, 70% value area,
maximum span 6,000 rows, no smoothing. Copy the Phase 1 backend: integer keys
`floor(low/width)` through `floor(high/width)` inclusive; uniform candle volume
over touched rows, including a high exactly on a boundary. POC ties choose the
lowest key; value-area expansion chooses the larger neighboring mass and ties
go upward. YVAH/YPOC/YVAL and ONPOC retain bin-base coordinates. These are
candle estimates of volume at price, not observed trade-level distributions.

Only confirmed constituent chart bars closing at or before 09:25 enter the
snapshot. Calculate exactly when the terminal bar confirms, with P its close;
exclude 09:25–09:30. Freeze prices, reason, fallback category, region/profile
identity, confluence and all selection inputs. Record last included open/close,
cutoff and historical reconstruction versus realtime observation where known.
Later bars cannot revise the snapshot. A missing exact terminal bar becomes
unavailable at the first subsequent bar; it cannot trigger a late substitute.
Invalid/missing/negative volume, zero profile total, overflow, partial initial
history and missing bars are explicit unavailable statuses. Individual zero
volume bars are allowed if period total remains positive. Never carry a prior
day's pivot as today's output. Unsupported chart types/timeframes display a
clear message. Reloads reconstruct from the same available bars/settings;
feed corrections or settings/history changes may alter reconstruction.

## N1/E1 control and ledger

Use only the frozen overnight distribution. Normalize masses by its total.
Detect interior equal-height maximum plateaus with strictly lower adjacent
rows; representative is the lowest plateau key. For peak p, search each side
until first strictly higher row or domain end, taking the minimum encountered
mass. Saddle s is the larger side minimum, d = p−s. Require p ≥ 0.20 times
global maximum and d ≥ 0.10 times global maximum. Grow contiguous rows whose
mass is ≥ s+0.5d. Rank by descending height, descending prominence, ascending
representative price; reject representatives less than two rows apart. Keep
eight regions, retain omitted/rejected counts and stable region identities,
flag all intersecting regions, never merge. Retain the uncapped candidates for
ambiguity/cap accounting. LVNs between disjoint adjacent regions use the lowest
trough plateau (lowest-price tie) and mass ≤ 0.25 of the smaller peak, cap seven.

E1 requires parent width ≥ two rows and an observed outside neighbor on the
corresponding side. Border qualifies if (inside−outside)/p ≥ 0.10. Lower boundary
is lower-key × width; upper boundary is (upper-key+1) × width. Uncertainty is
[B−width/2, B+width/2]. Maximum sixteen retained edges. Domain-truncated sides
are unavailable. Retain qualification/rejection, parent and profile identities.
POCs, peaks, value boundaries and E1 edges remain separate objects.

## Exact selector, fallback and confluence

Let b = max(2 minimum ticks, width/2). If P < YVAL−b, choose YVAL,
`Prior-value reclaim boundary`. If P > YVAH+b, seek N1 regions containing P
within their full bin interval, inclusive at both bounds
[lower-key × width, (upper-key+1) × width], and with qualified lower E1 boundary
> YVAH+b. Shared-boundary membership may therefore expose ambiguity.
Exactly one unambiguous eligible region gives that original boundary,
`Hold higher auction`. Cap omissions, overlapping competing parents or missing
edge evidence that prevent uniqueness instead give YVAH,
`Prior-value boundary fallback`, categorized absent/ambiguous/incomplete.

Otherwise choose YVAL when ONPOC < YPOC−b (`Overnight value shifted lower`),
YVAH when ONPOC > YPOC+b (`Overnight value shifted higher`), and YPOC otherwise
(`Balanced fallback — no unique directional divider`). Exact tolerance
boundaries belong to this final branch; strict inequalities are never rounded.
Balanced and prior-boundary fallbacks are labeled and dashed/muted. Optional
strict suppression defaults off. No tie is resolved from later price action.

For a selected value reference, report every independently generated qualified
E1 boundary within one row, preserving its price, side, parent and profile IDs.
Confluence never snaps, averages or otherwise changes the selected price.

## Presentation defaults

One timestamp-based horizontal line per ready day, from 09:25 to 16:00 New
York, drawn only after the cutoff confirmation; no plot connects days. Keep
30 historical lines by default, bounded 1–100. Label price and reason. Optional
edge-uncertainty shading defaults off. Diagnostic table shows contract/timeframe,
date/timezone/cutoff, last included bar, source periods, all five inputs, pivot,
reason, parent/profile, confluence, fallback and ready/waiting/unavailable status.
Unavailable prices use na. Optional acceptance defaults on: post-cutoff confirmed
bars only; two consecutive closes > pivot+b are bullish, two < pivot−b bearish,
otherwise unresolved. Reset counters each trading day; acceptance cannot alter
the pivot.

## Verification fixed before results

Use one contract and settings on October 1, 2 and 5, 2026 only. No additional
Verniman source/target dates or hidden answers may be inspected. For each date
retain a pre-cutoff observation (no today's line), confirmation of the terminal
bar, every frozen field, a visible 09:25 line start, an RTH advance with identical
snapshot, and an independent Replay restart/reload reproducing all fields with
adequate history. Retain screenshots, settings, source hashes and failures.

Synthetic checks cover every branch, exact tolerance boundaries, POC/VA ties,
N1 plateau/prominence/overlap/endpoints, E1 width/contrast/coordinates/uncertainty,
invalid and zero volume, partial sessions, missing terminal, resets, NY DST and
identical-prefix invariance under radically changed post-cutoff bars. Run the
owning study focused gate and documentation checks. Translated-model success
is distinct from actual Pine compilation, runtime and Replay verification.

Acceptance requires native compile/add without errors, all three date checks,
private save as `Verniman Pivot Levels`, a new saved layout named
`Verniman Pivot Levels — Verification`, and reload/readback showing exact saved
source, unchanged settings and indicator attachment. A browser/account/access
block is retained as incomplete, never counted as a pass.
