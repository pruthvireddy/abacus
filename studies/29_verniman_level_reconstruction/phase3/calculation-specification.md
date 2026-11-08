# Phase 3 calculation specification

The [frozen protocol](protocol.md) resolves ambiguities in the full
[Phase 2 implementation contract](../phase2/phase3-specification.md).
[settings.json](settings.json) is the global control, unchanged across sessions.
The [local model](../src/phase3_model.py) is an independent specification oracle;
it does not execute [Pine](../indicator/verniman_levels_phase3.pine).

## Identified distributions

Retain the latest completed RTH, overnight prefix through cutoff, current-week
prefix, previous completed week and explicit composite. Each input carries
contract/feed/adjustment/tick, window and member identities, lower/upper row
boundaries on the zero-anchored grid, raw and normalized mass, total, measurement,
last confirmed bar, coverage, missing-volume/overflow/readiness and code/settings/
input identities. Empty, invalid, incomplete and incompatible inputs return an
unavailable reason rather than a zero detection or old prices.

The measurement remains Phase 1's uniform allocation of chart-bar volume across
inclusive touched bins. Sixteen ES ticks are four points. A bar high on a boundary
touches that bin. Finer rows do not recover observed volume at price. Original
VAH/POC/VAL use bin-base coordinates, lowest-price modal ties and upward-first
adjacent VA ties. N/E geometry uses whole row intervals and shared outer borders.
A different geometry is explicit, not a silent change to the original 19 fields.

## N1 regions and LVN intervals

Interior maximal equal-height plateaus need strictly lower adjacent rows.
Representative is the lowest-price plateau row. On each side search to the first
strictly higher mass or the domain end; take that side's minimum. With peak `p`,
saddle `s` is the larger minimum and prominence `d=p-s`. Qualify at
`p >= 0.20 max(mass)` and `d >= 0.10 max(mass)`.

Rank by descending height, descending prominence, ascending representative row.
Greedily reject representatives less than two rows from an already retained
representative. Grow from the complete plateau through contiguous rows with
`mass >= s+0.5d`. Preserve integrated original mass, plateau bounds, full region
interval, overlaps, endpoint truncation and rejection reasons. Regions can overlap;
they are never merged. Stable IDs derive from identified profiles and row keys.

Between adjacent disjoint regions in representative-price order, select the
lowest contiguous plateau in the intervening gap, with lowest-price tie.
Require trough mass at most one quarter of the smaller parent peak. Keep its
full interval, parent IDs and relative depth. Endpoints are not automatic LVNs.
Touching or overlapping parents cannot produce a fabricated intervening trough.

Calculate the full ledger before applying presentation caps. Display at most
eight HVNs by peak rank and seven LVNs by ascending trough height then price.
Preserve omitted IDs/counts. Ranking is a presentation rule, not pivot selection.

## E1 boundaries

An E1 HVE candidate needs a retained HVN parent at least two rows wide and an
observed outside neighboring row on that side. Require
`(inside_mass-outside_mass)/parent_peak >= 0.10`. The lower boundary is the first
region row's base; the upper is one row beyond the last base. Emit boundary `B`
and uncertainty `[B-row/2, B+row/2]`, side, adjacent masses, contrast, parent ID,
readiness and categorical engineering evidence status. No calibrated probability.

A domain-truncated side is unavailable. One-row parents and shallow borders carry
explicit rejection reasons. POC, a node representative and VAH/VAL are different
objects; none is relabeled HVE. All qualified parents remain eligible even if
presentation-omitted. Rank edges by parent rank then lower/upper side; display at
most sixteen and retain the full calculation ledger and omitted IDs/counts.

## Explicit composite

Use the three expected completed 09:30–16:00 RTH weekdays before the snapshot,
Friday for Monday, with no holiday substitution or bespoke per-day membership.
Canonicalize order; reject missing/duplicate/partial members and differing
contract, feed, adjustment, tick/grid or measurement. Sum compatible raw masses
on shared grid keys. Retain membership, inclusion reason, mass, coverage,
exclusions and row-sum lineage. Apply unchanged N1/E1. This is an explicit
composite histogram, not automatic balance discovery.

## PBT arithmetic and timing

P1 uses declared center `C` and edge `E`: `T=2C-E`. For intervals, bounds are
`[2C_low-E_high, 2C_high-E_low]`. P2 uses ordered balance bounds `L<H`:
upper `[2H_low-L_high, 2H_high-L_low]`, lower
`[2L_low-H_high, 2L_high-H_low]`. Require disjoint interval bounds
`L_high < H_low` so the complete declared uncertainty has positive width.
Retain unrounded terms/intervals. Round lower bounds down and upper bounds up to
the instrument tick for presentation; these are uncertainty intervals, not odds.

Anchors require stable ID, price interval/precision, reference period/measurement,
contract, observed/confirmed times, evidence, reason and explicit-source versus
analyst-proposed status. Both timestamps must be at or before cutoff in order; independently
supported causal evidence is a separate requirement. Entering a time cannot prove
historical availability. Missing, unsupported, malformed or later-confirmed anchors
produce unavailable causal projections. No plausible price default or back-solving.

If the declared center is explicitly the midpoint of a complete known range,
reflecting one exact bound is flagged as the opposite existing boundary. Do not
present that identity as a new external target. Preserve retrospective arithmetic
separately, never in the causal map. Keep reconstruction readiness distinct from
source historical availability, which can remain null. The local provenance ledger
and Pine input workflow are described in [installation-replay.md](installation-replay.md).

## Frozen snapshot and extraction

Use confirmed bars with close at or before 09:25 New York and require the exact
09:20–09:25 final interval for five-minute data. Copy distributions/candidates/
anchors at that boundary and reset by futures trading date. Later developing bars
or later-confirmed anchors cannot modify that map. Unchanged input history and
settings are necessary for restart reproducibility.

Local output retains the full ledger; Pine uses bounded arrays, a selected-profile
row/candidate table and bounded drawings. Pine cannot directly read local JSON or
provide a general filesystem export. Source/code/settings/input hashes remain in
the local capture ledger and are transcribed/linked to browser captures. Actual
native behavior and performance remain unverified until the access gate is resolved.
