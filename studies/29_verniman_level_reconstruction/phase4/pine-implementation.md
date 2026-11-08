# Phase 4 Pine selector implementation

The separate [Pine derivative](../indicator/verniman_levels_phase4.pine) keeps
TradingView indicator title **Verniman Levels** and identifies implementation
4.0.1 and unchanged selection control 4.0.0 in its own header/table. It adds the
frozen [selection protocol](protocol.md) and
[settings](settings.json) to the original Phase 3 candidate backend. These are
engineering hypotheses. Native outcomes belong in [verification.md](verification.md);
this implementation guide is not a native compile or empirical-fidelity receipt.

All earlier Phase 3 Pine sources and the original v3.0.0 control remain unchanged.
This derivative does not edit the separate saved **Autopivot Levels - Daily**;
concurrent external display revisions are attributed in the verification record. The inherited
Phase 3 header describes that candidate backend; Phase 4 selection is confined
to marked `PHASE4 BEGIN` / `PHASE4 END` additions.

## Construction identity and native corrections

The embedded candidate implementation is now **3.0.2**, retaining control 3.0.0.
The [correction record](candidate-implementation-corrections.md) pins all earlier
sources and explains the native compiler and Replay-contract metadata fixes.

The candidate mathematics, clocks, thresholds, histogram allocation, original
19 fields, three-RTH composite and manual-anchor P1/P2 policies are unchanged.
The Phase 4 derivative includes two implementation corrections confirmed while
compiling the separately retained Phase 3 3.0.1 source:

- Rename reserved helper parameter `text` to `cellText` in `f_p3Cell`.
- Rename last-bar HVN drawing locals `low`/`high` to `zoneLow`/`zoneHigh` to avoid
  shadowing chart built-ins already used in that scope.

Neither compiler rename changes a calculated candidate. The subsequent 3.0.2
metadata fix uses `ticker.standard(syminfo.tickerid)` for contract identity,
manual-anchor comparison and the unhashed input fallback. It retains the raw
chart identifier separately in frozen `rawChartContext` tooltip metadata, never
in semantic candidate IDs. Standard anchor contracts remain explicit, for example
`CME_MINI:ESZ2026`; all original causal-anchor requirements still apply.

The original v3.0.0 and 3.0.1 sources remain byte-preserved. Removing all marked
Phase 4 blocks, the descriptive header word `backend` and introduced blank-line
differences restores the complete 3.0.2 candidate source. The correction record
identifies its limited diff from earlier versions. This is a source-preservation
guard, not numerical execution or native parity. No unrelated profile-method
return change is made.

The selectable adapter pool is explicitly bounded to the **original 19 saved
references**, all frozen E1 edge-ledger records and causal PBT arithmetic whose
anchors passed the generator. Only qualified edges and eligible exact,
nonidentity PBT points can become targets. Rejected edge records and nonexact
causal intervals remain inspectable as exclusions. The full HVN/LVN ledgers
remain in the inherited candidate laboratory; their centers/intervals are never
inserted into the destination pool as invented exact prices. Composite E1 edges
are included. Internally calculated composite VA fields are not additional
members of the saved original-19 interface and are not introduced here.

## Frozen pivot controls

P0 is the pre-existing contextual hypothesis adapted to Phase 3's strict
expected-prior-weekday RTH. This differs from the saved Autopivot's latest-
observed-RTH convention and receives its own identity. All P0/B0/B1 outputs
require the same ready prior RTH and ON inputs, finite ordered prior value,
ONPOC, cutoff close `P` and exact five-minute included interval.

With `b=max(2 ticks, half a row)`, P0 selects original YVAL below `YVAL-b`.
Above `YVAH+b`, it selects the qualified lower E1 of exactly one unambiguous
containing ON parent, above that value boundary. Its conservative comparator
gates use the top eight ranked parents, with any parent cap omission, relevant
overlap, missing lower edge or absence yielding the labeled YVAH fallback.
Within/near prior value, ONPOC below/above `YPOC +/- b` chooses YVAL/YVAH;
otherwise POC is a balanced fallback. Exact tolerance boundaries remain in the
within/near branch. Fallback pivots are displayed as such; both target branches
abstain.

B0 selects YPOC. B1 selects the nearest original YVAL/YPOC/YVAH to `P`, breaking
equal distance by lower price and then stable ID. The three pivot choices are
saved together. The **Pivot policy** input defaults to P0 and chooses which
frozen pivot drives both saved destination policies. Comparator controls do not
change the saved Autopivot or turn its alternate reference into a target.

Pivot reason codes include `P0_BELOW_VALUE_RECLAIM`,
`P0_HIGHER_AUCTION_LOWER_E1`, `P0_PRIOR_VAH_FALLBACK`,
`P0_ON_VALUE_SHIFT_LOWER/HIGHER`, `P0_BALANCED_FALLBACK`,
`B0_FIXED_YPOC`, `B1_NEAREST_VALUE` and `ABSTAIN_REQUIRED_INPUT`.
The reason, fallback detail, source ID, uncertainty and every nearby E1
confluence index are retained without snapping or moving the original price.
The confluence tooltip shows at most 16 IDs and the full count; the complete
`confluenceMembers` array remains available alongside the reference ledger.

## Bounded branch destinations

Eligible original destination coordinates are VA boundaries, full/RTH/ON range
extrema, qualified E1 boundaries and exact causal nonidentity PBTs. POCs, prior
close, HVN centers, LVNs, unsupported GAP/ATH/intraday families and unsupported
PBTs cannot become targets. Unmeasured VIX/CVD, today's eventual RTH open and
post-cutoff reactions are absent from the selector.

D0 visits eligible prices nearest outward from the pivot. It is a declared
price-distance baseline, not a claim about source scenario order. D1 first seeks
the opposite boundary of the selected auction on the applicable side: RTH
YVAL→YVAH bullish, YVAH→YVAL bearish, or a selected lower E1→the same parent's
qualified upper E1 bullish. It then fills slots with nearest range extrema and
finally external E1/VA boundaries or exact PBTs. Every subsequent target must lie
strictly more than `b` beyond the last selected coordinate in its branch.

Both policies save at most three targets per branch, strictly ascending bullish
and descending bearish. D1 can skip nearer intervening marks because of its
structural-stage priority; it records that choice instead of presenting price
sorting as a learned sequence. Missing eligible references leave partial ladders.
Unavailable/fallback pivots yield unavailable branches. No desired source price
or per-date exception is added to the candidate pool.

Exact duplicate prices form groups of all eligible original IDs/roles, ordered
lexicographically for stable presentation. A target's presentation reference is
the smallest ID. Its separate `originatingIndex` records the actual role that
justified an auction/range/external-stage selection. No coordinate or interval
is averaged. Overlapping uncertainty intervals at differing prices remain
separate groups.

Selection reasons are `OWN_AUCTION_EXIT`, `RANGE_EXTREME`,
`EXTERNAL_BOUNDARY_OR_PROJECTION` or `DISTANCE_BASELINE`. Per-candidate branch
ledgers preserve readiness/exclusion, wrong direction or buffer, duplicate
membership, spacing, structural skipping, target-cap and selected-rank reasons.
The candidate snapshot retains its original price/interval, family, role,
window/auction/parent, side, readiness and cutoff.

## Timing, tables and drawing bounds

`P`, all three pivot decisions and both D0/D1 branch decisions are copied once
when the authoritative completed 09:20–09:25 bar confirms. They reset by futures
trading date. Later bars update inherited developing displays only and cannot
mutate Phase 4's reference/group/pick arrays. A missing exact terminal boundary
never produces a late substitute or stale prior-day selection.

The Phase 4 table sits at bottom right. Implementation 4.0.1 limits visible
branch-decision captions to 48 characters plus an ellipsis; the full decision,
original IDs and source metadata remain in tooltips/arrays. This display-only
correction was verified natively after the original 4.0.0 overflow was retained.
The frozen policy and selected prices do not change.

The **Selections** view shows P0/B0/B1, configured
D0 or D1 target ranks, readiness and input accounting. **Pivot alternatives**
and four D0/D1 branch-ledger views expose 16 original references per page;
hover cells for full source IDs, raw intervals, origin and reasons. The top row
shows policy identities, cutoff, last included interval, `P` and `b`.

The overlay adds one pivot and at most six target lines/labels, width one,
from cutoff to 16:00 New York. Main pivot is purple, bullish targets green,
bearish targets red; pivot fallbacks are dashed. The inherited laboratory
remains independently toggleable. Turn off unwanted inherited families/zones
for a sparse selector view; their calculations and ledgers remain retained.

The existing ceilings of 100 lines/labels and 32 boxes accommodate the
source-derived simultaneous bound of **67 lines/labels and 18 boxes**: inherited
maximum 60 plus seven Phase 4 objects. Old Phase 4 drawings are deleted before
recreation on the last bar. These are declared object counts, not native runtime
measurements. Algorithm arrays remain bounded by the inherited five profiles'
6,000-row limits; there is no presentation cap applied to selection input merely
to improve performance.

Pine tables/arrays have no lossless local JSON export. Retain screenshots and
explicit transcriptions with source/settings/input hashes, or separately run the
independent local model on pinned same-feed bars and distinguish that execution
path. Tooltips abbreviate very large duplicate groups to 16 IDs, while their
full member-index arrays and paginated reference ledger retain the complete group.

The runtime contains no hardcoded per-date selection overrides. Capture and
comparison in this phase are restricted to the ten authorized training dates;
development/hidden-test Replay and answer sources remain prohibited. Changing
an inspection or policy input recomputes the chart history, so equal settings,
feed/history and explicit source hashes are required for restart comparisons.

Current official [Pine array documentation](https://www.tradingview.com/pine-script-docs/language/arrays/)
supports numeric and string sorting used here. String-ID ties are sorted
explicitly rather than relying on numeric-sort stability. Local source guards
and independent specification tests do not execute Pine; actual compile,
Replay, saved source and performance results must be recorded separately.
