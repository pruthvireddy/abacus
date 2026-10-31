# Protocol 2.0.0 — ranked pivot and Globex VWAP statistics

Frozen definitions for the authorized repository-only extension, 2026-10-31.
The [original protocol](protocol-1.0.0.md) remains applicable unless explicitly
extended here. The completed `20261031_repo_v2` results have been viewed. This is
retrospective exploratory extension after prior exposure, not an untouched holdout.

## Populations and coverage

Requested dates remain 2020-01-01–2026-10-30. Use only the pinned
`es_contract_session_indicators__1.0.0` and pivot release in the input lock.
Retain three populations independently: `pivot_matched_rth` preserves every
baseline source/exact quoted contract/calendar/feature-quality decision;
`vwap_only_rth` needs no pivot but requires the same anchor-to-16:00, RTH and
indicator readiness rules; `vwap_only_full_globex` requires a complete 18:00–17:00
session, native EMA6 readiness and valid cumulative VWAP throughout its expected
observations. The pinned pre-2021-06-28 16:15–16:30 scheduled halt is a known
closure. It contributes no exposure. Unknown gaps clear comparison state.
No missing late-session tail invalidates otherwise eligible RTH statistics.
Pivot/VWAP comparisons use only the matched population. Events carry memberships;
report selections never create extra events. RTH and Globex state machines have
different initializations and are explicitly labeled observation scopes.

## New events, episodes and conditions

At each completed three-minute close compare EMA6 or price close with the
contemporaneous completed one-minute HLC3-volume VWAP. Both lines move; price
need not be on the EMA6 crossing side. Equality carries the last strict side;
unknown clears it; first strict side initializes without crossing. At RTH seed
price from actual 09:30 open, EMA6 and VWAP from completed values by 09:30.
Globex starts uninitialized at the anchor; never count a VWAP reset. Sections
never reset state. Existing `ema_events` continues to mean EMA6–pivot events.
`ema_vwap_aligned` retains its original context meaning.

Events use bar-open section membership and close information time. Save full
native completed snapshots and stable links; confirmation outcomes link the
confirmation snapshot. Ordinals count independently by reference/series/scope
and day or section. EMA-reference recross is the next reverse EMA event, distinct
from a reverse price event. For 15/30/60-minute no-recross probabilities require
the complete RTH window, including when a reverse is already observed. Within
complete windows a reverse is false and absence is true. Late/missing windows
remain null/censored; the independently observed next recross is still retained.

For S14 observe each EMA reference cross for 30 minutes, within RTH. Separate
simultaneous second-line crosses, already-beyond-second-line states, equality
with the other line at the start (outside the strict at-risk denominator), strict
second-line crossings before a reverse first-line cross, reverse-first outcomes,
neither within a complete window, and censored windows. A tie at an observed
close has no inferred intrabar ordering. Direction is the originating cross.

Opening configuration uses actual opening price above both, below both, between,
equal-boundary or unknown; retain EMA6 opening configuration separately. Opening
absolute pivot–VWAP distance is retained in points and
`10000*abs(VWAP-pivot)/pivot` basis points. Fixed bands are `<5`, `5–<15`,
`15–<30`, `>=30` basis points and unknown, frozen before new conditional results.
Cloud support requires directional EMA20/50 ordering and both native five-minute
15-minute slopes in that direction; opposition requires all three opposite.
Mixed/flat and unknown stay separate. Persistence compares opening-range endpoint
states with AM and PM endpoints, retaining equality/unknown and denominators.
S18 remains only a fixed-pivot retest, with its original definition.

## Outcomes and saved statistics

All forward outcomes remain RTH-only, start at event or confirmation completion,
exclude earlier signal-candle extremes, and require complete 15/30/60-minute
paths; 30 minutes is primary. Retain section/day-end context and null reasons.
S06/S07/S08/S18 reuse exact baseline pivot evidence. Recurrence retains all valid
zero-event days and price/EMA comparisons use common named populations.

First-cross times are completion times measured from 09:30 RTH or 18:00 Globex,
including section selections. Timing bins retain no-cross days in their
denominator, with no-cross as a separate category. The final bin includes the
session closing endpoint and is labeled inclusive.

Save overall, annual, calendar-month and trailing 20/60/120 eligible-session
summaries at the requested cutoff. Each earlier comparison excludes that recent
window. Keep all events, first per day, first per section, directions and primary
30-minute conditional panels. Save units, numerator where defined, valid
denominator, candidate/missing/censored support, distinct days and actual dates.
Use 2,000 noncircular five-observed-session moving-block replicates, seed 20261031,
preserving full day dependence; fewer than 30 supporting days is sparse.
Broad slices are exploratory, not profitability evidence.

## Gates and publication

The [implementation matrix](implementation-matrix.md) maps all 20 questions.
Freeze sources/settings/input pins/locked environment and successful synthetic
tests before execution. Recalculate unchanged baseline evidence and reconcile
every baseline ledger field and summary cell (absolute tolerance 1e-8, relative
1e-11 for finite numeric cells; identities/nulls/booleans exact). Independently
reconstruct new events, episodes, exposures and summaries from retained inputs.
Prepare two bounded saved Narada sources before sealing; use catalog `analyses`
for the new priority reports and the original six with correct separate run IDs.
Required app/source/HTTP/browser checks precede seal. Every failed attempt remains
retained and only observed successful exits may be recorded as passed. No hosted
deployment, acquisition, release rebuild or trade simulation is authorized.
