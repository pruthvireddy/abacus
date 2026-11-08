# Phase 3 Pine implementation and inspection

The separate [Pine derivative](../indicator/verniman_levels_phase3.pine) retains
TradingView title **Verniman Levels**, with Phase 3 v3.0.0 in its header and status
table. It implements the [frozen protocol](protocol.md) and
[settings](settings.json). These are experimental engineering hypotheses, not
Verniman’s recovered algorithms. Native compilation and runtime behavior remain
unverified because the browser blocked the separate-layout copy submission.
A source review or Python test does not execute Pine.

## Baseline preservation

The original [Phase 1 script](../indicator/verniman_levels.pine) is unchanged.
The derivative embeds its arithmetic, state updates and 19-field capture without
altering those lines. Additive hooks are marked `PHASE3 BEGIN` / `PHASE3 END`.
Stripping those blocks, reversing the indicator declaration’s added box limit
and Phase 3 header comments, and normalizing introduced blank lines restores
the Phase 1 source. This is a source-level preservation check; actual 19-field
parity in native Pine still requires Replay verification.

The inherited profile is uniform allocation of each chart bar’s volume across
inclusive touched rows. It remains an approximation, not observed traded volume
at price. Finer bins cannot recover missing volume-at-price information.

## Frozen distribution interface

The Phase 3 control accepts `CME_MINI:ESZ2026`, standard 5-minute candles, 16-tick
rows, 70% value area and 09:25 New York. ETH coverage is enforced through the
inherited continuity gates. Other inherited baseline configurations can still
calculate baseline references, but new Phase 3 distributions are unavailable
outside this frozen control.

Five identified distributions are copied at the exact completed cutoff:

- Latest expected completed RTH, including its 09:30–16:00 source interval.
- Overnight prefix from 18:00 through the cutoff.
- Current futures-week prefix through the cutoff.
- Adjacent previous completed futures week.
- The fixed last three expected completed RTH sessions.

Each keeps contract/feed, adjustment qualification, tick size, grid origin,
measurement, row bounds/raw mass, total mass, last completed close, coverage,
volume/overflow state, code/settings/input identities, expected versus actually
observed sessions and exclusions. The table’s included-bar tooltip shows the
5-minute opening and closing boundaries. Missing expected RTH/week placeholders
retain the expected interval and empty observed membership, not fabricated rows.

The composite sums compatible row keys, keeps member masses and source lineage,
and rejects a missing, duplicate, incomplete, incompatible or future member.
Its member ledger is frozen with the map; later cache rotation cannot rewrite
it. A composite distribution does not establish a balance.

## N1/E1 ledger and bounded chart

The detector uses nearest-strictly-greater stacks and a range-minimum tree for
literal N1 prominence. Binary-search range minima give the same inclusive
region expansion without rescanning the whole profile for every peak. Tied
ranking keys are explicitly resolved by ascending row rather than relying on
sort stability. The full maxima/rejection ledger, accepted region bounds/mass,
plateaus, endpoint flags, overlap flags, LVN parent pairs, and both E1 sides are
retained in arrays. Threshold failures and presentation omissions remain visible.

Select an **Inspected frozen distribution**. The table offers Summary, raw Rows,
HVN ledger, LVN ledger, HVE ledger, Composite and Anchors / PBT. Ledger views show
16 entries per page; increase the page input to inspect later entries. Hover
cells for full stable IDs, source periods, numerical evidence and reasons. The
Summary lists qualified counts and cap omissions independently of ledger size.
LVN diagnostics distinguish `trough / smaller parent peak` from relative depth
`1 - that ratio`. Edge intervals are the shared grid boundary plus/minus half
a row, supported by the identified inside/outside masses.

Only the selected distribution is drawn. Independent family toggles control
candidate zones and edges. HVNs cap at eight, LVNs at seven and HVE boundary
lines at sixteen; calculations and rejection arrays remain uncapped within the
6,000-row input bound. E1 also evaluates accepted parents omitted from HVN
presentation. The cap rank never selects a pivot or ordered targets.

The configured drawing ceilings are 100 lines, 100 labels and 32 boxes. The
source’s maximum simultaneous allocation is 41 inherited baseline lines/labels,
16 candidate HVE lines/labels, three PBT lines/labels and 18 boxes (eight HVN,
seven LVN, three PBT). HVE uncertainty is retained in its table/label; its dotted
line denotes the shared grid boundary. This is a source-derived allocation
bound, not a measured native runtime result. The boxes/lines are recreated only
for the last chart bar and old objects are deleted first.

## Manual-anchor input workflow

Pine cannot read local JSON. Maintain the local anchor ledger first, retain its
hash and evidence, then transcribe its four encoded anchor records into C, E,
L and H inputs. All four inputs default to empty; no anchor price is invented.
The encoder must produce exactly these thirteen pipe-delimited fields, with no
pipe character inside a field:

```text
id|low|high|contract|reference-period|measurement|observed-ms|confirmed-ms|evidence|reason|explicit-source OR analyst-proposed|causal-support true OR false|reading-precision
```

Times are integer Unix milliseconds; the contract must equal the actual chart
`syminfo.tickerid`. Include interval bounds even for exact prices (`low = high`),
a stable ID, reference period, measurement, source/selection evidence and reading
precision. Enter a local code SHA-256 and market-input capture identity in the
provenance inputs when available. Pine cannot calculate those hashes or verify
that manually entered values identify the actual feed history.

The global **Independent pre-cutoff evidence checked in local ledger** checkbox
is false by default. An eligible anchor requires that attestation plus its own
causal-support field, complete provenance, consistent stable IDs/intervals,
compatible contract and `observed <= confirmed <= cutoff`. A timestamp or an
attestation alone does not prove historical availability. The table calls this
recorded eligibility and retains `source_historical_available_at = null`.
Different measurement descriptions are retained rather than prohibited merely
because a center and boundary use different constructions.

P1 calculates `[2C_low - E_high, 2C_high - E_low]`. P2 separately calculates
upper `[2H_low - L_high, 2H_high - L_low]` and lower
`[2L_low - H_high, 2L_high - H_low]`, requiring separated L/H intervals. Bounds
are rounded outward to the price tick; unrounded values stay in the projection
ledger. Recorded confirmation and eligible reconstruction readiness are
separate fields; unavailable projections have no reconstruction-ready time.

Unsupported or later-confirmed anchors never draw causal PBT candidates. Any
available numerical illustration remains in the explicitly noncausal table
with its rejection status. The complete-range midpoint checkbox additionally
requires consistent exact L/H/C/E records. Its opposite-existing-bound identity
is labeled explicitly and is not drawn as a new external target. No automatic
anchor selection or target fitting is implemented.

## Installation and Replay when access is available

1. Use a separate private study layout that preserves Phase 1. Do not retry the
   security-blocked layout action through alternate controls or browser routes.
2. Create a new private indicator in Pine Editor, paste the complete derivative,
   save it privately and attach it only to the separate study chart. Record
   actual compiler/runtime messages; no successful compilation is claimed here.
3. Inspect the declared symbol, standard 5-minute candles and ETH, with preceding
   history sufficient for a complete previous week. Keep the frozen defaults
   and empty anchor ledger for the first pass.
4. Verify October 1, 2 and 5 first. Select 09:25 in Replay and advance only as
   needed for the table to record the **09:20–09:25 confirmed bar**. Save baseline
   values, all distribution rows/metadata and candidate ledgers, code/settings/
   input identities and browser evidence before advancing.
5. Advance into RTH and restart at the same cutoff/settings/history. Compare all
   original 19 fields, expanded candidates, intervals, IDs, membership and anchor
   statuses. A later-confirmed anchor must remain unavailable at the cutoff.
6. Retain and hash all seven additional training maps before opening any of their
   targets. Development October 15–20 and hidden October 21–27 remain closed.

Use the actual included-bar interval as authoritative; Replay’s cursor alone is
not a completed-bar claim. Changing an inspection page/toggle causes TradingView
to recompute from history; compare the same retained feed/settings. Drawings
begin at the snapshot cutoff and cannot backdate availability.

## Extraction and performance limits

Pine arrays and table tooltips are inspectable in the chart, but this script has
no lossless automatic JSON/CSV export of them. Ordinary chart-data export does
not serialize these arrays. Retain table screenshots/transcriptions with exact
IDs or use the separate local specification model against independently pinned
bars, clearly labeled as a different execution path. Source/hash inputs cannot
certify matching browser bytes.

Detectors run at the completed cutoff rather than on each developing bar.
Their input arrays are capped at 6,000 rows; presentation does not truncate
calculation. Native wall-clock performance, tooltip usability, memory behavior,
and platform limits have not been measured. If TradingView reports a runtime
limit, retain the exact failure and optimize the same algorithm under a new
code identity; do not silently reduce rows, discard candidates or retune rules.
TradingView’s current [limitations documentation](https://www.tradingview.com/pine-script-docs/writing/limitations/)
reports per-loop and dataset execution limits. Its [type-system documentation](https://www.tradingview.com/pine-script-docs/language/type-system/)
describes reference objects and shallow copying; this implementation explicitly
copies mutable histogram/member arrays used by the frozen map.
