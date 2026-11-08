# Phase 3 frozen protocol

Protocol 3.0.0 · experimental engineering control, not Verniman’s recovered algorithm.

The user authorizes Phase 3 only. Preserve Phase 1 and Phase 2 byte identities.
Settings are frozen in [settings.json](settings.json). N1/E1 is implemented literally
from the [Phase 2 contract](../phase2/phase3-specification.md). No parameter sweeps,
per-day settings, automatic anchors, balance discovery, LIS/pivot selection, ordered
targets, profitability, Narada publication or deployment.

## Resolved ambiguities before execution

- Raw row mass and normalized mass are retained. Comparisons on raw mass are
  equivalent to normalized comparisons within one positive-total distribution.
  No smoothing or padding. Domain gaps are zero-mass rows only when observed
  bars and compatible coverage establish the domain; missing observations fail readiness.
- Detect maximal equal-height plateaus. Interior plateaus require both neighbors
  strictly lower. Endpoint maxima are logged as rejected, not implicit LVNs.
  Representative is the lowest-price row. Each side searches from its adjacent
  row through the first strictly higher row, or the endpoint. Its minimum includes
  that search interval; equal peaks do not stop it. Saddle is the larger minimum.
  Both thresholds are inclusive. Grow from the whole plateau while mass >= saddle
  + 0.5 prominence, even if that causes overlapping regions; never merge.
- Rank qualifying peaks by descending height, descending prominence, ascending
  representative row; greedily reject a peak within strictly less than two rows
  of an already accepted representative. IDs use profile identity and row keys,
  independent of rank. Region price interval uses lower edge of first row through
  upper edge of last row. Integrated mass sums original rows.
- Compute the full qualified ledger before presentation caps. Eight HVNs are
  displayed by peak rank. Flag overlaps on all retained regions. LVNs use adjacent
  disjoint regions in ascending representative-price order; no trough is invented
  between overlapping/touching regions. The lowest contiguous plateau in the open
  intervening gap wins (lowest-price tie), qualifying at <= 0.25 smaller parent
  peak. Rank LVNs by ascending trough height then price. Retain rejections.
- E1 operates on every retained parent, even presentation-omitted parents. Width
  >= two rows and an observed outside neighbor are required separately per side.
  Contrast = (boundary-inside mass - adjacent-outside mass)/parent peak >= 0.10.
  Lower boundary = lower row base; upper = upper row outer boundary. Interval
  is boundary +/- half a row. Rank edges by parent peak rank, lower before upper.
  Caps of 7 LVNs and 16 edges affect presentation only; omitted IDs/counts persist.
- Composite membership is the last three expected completed RTH weekdays before
  the snapshot (Friday for Monday); fixed clocks, no holiday substitution. Require
  every member, complete 09:30–16:00 coverage, identical contract/feed/adjustment/
  tick/grid/measurement. Reject duplicates, missing or partial members; canonicalize
  order. Preserve each member’s mass, exclusions and row-sum lineage. No balance claim.
- P1 and P2 remain separate. Reject nonfinite, reversed, inconsistent or mixed-
  contract anchors. Require observed <= confirmed <= cutoff, a reference period,
  evidence, reason and explicit independent causal-evidence support, in addition
  to entered times. Missing/unsupported/later-confirmed anchors give unavailable
  causal output. Preserve retrospective illustrations separately. Source historical
  availability stays null where unsupported. Known complete-range midpoint
  reflection is marked opposite-existing-bound identity. Round interval bounds
  outward to ticks; retain unrounded arithmetic. Default anchor ledger is empty.

## Input, snapshot and first-pass order

Expose latest completed RTH, overnight prefix, current-week prefix, previous
completed week, and explicit composite distributions. Reuse Phase 1 clocks,
coverage, allocation, 6,000-bin and exact completed-boundary gates. Save metadata,
rows, total, last completed bar, readiness and code/settings/input identities.
Never fill missing data with a different contract or timeframe. Freeze copied
candidates/anchors at 09:25; later bars cannot modify them.

First verify native behavior on October 1, 2, 5 if access permits. Retain and hash
all seven additional training maps before reading any new target sources. If
market data or native access is unavailable, save an explicit per-date failure;
never label a baseline-only or fabricated map as an expanded map. Do not reveal
new answers while any of those seven maps is unavailable: preserve the possible
first pass for later recovery. Ten dates are training, never out-of-sample.
Development October 15–20 and hidden October 21–27 targets stay closed.

## Source selection and comparison

Use pinned release 13.0.0 via public loader with exact allowed date filters and
exact intake filenames. Preserve revisions, conflicts, uncertainty and null
availability. Inspect daily-plan, structural chart and later annotations in
separate strata; exclude execution arrows. New X inspection is in-app browser
only, no HTTP/API scraping. Do not expose unrestricted answer tables.

Global matching tolerance is 1 ES point for exact-price or interval gap. Require
family and known compatible reference window for primary coverage. Unknown
windows retain descriptive alternatives, with no construction-identity claim.
Use one-to-one maximum-cardinality/minimum-error matching within source
class/revision/family/window strata, deterministic ID ties; retain alternatives.
Report readable/eligible denominators, errors, counts, cap omissions, unmatched
source/generated candidates and timing/source suitability. Unmatched generated
candidates are not automatically false levels. No later reaction determines a hit.

## Verification and change control

Independent hand-worked synthetic tests are distinct from native Pine compilation
and Replay. Native checks require the declared ESZ2026/5m/ETH configuration,
cutoff, advance, restart, original 19-field parity, later-anchor rejection and
bounded drawing/performance observations. Log exact access restrictions.
Any later algorithm/settings revision gets a new identity and retains v3.0.0’s
first-pass outputs. No incomplete evidence is sealed.
