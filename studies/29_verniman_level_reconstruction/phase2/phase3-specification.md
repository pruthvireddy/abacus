# Phase 3 candidate-extension specification

Study 29 · design only · no Phase 3 implementation or selection is executed.

This specification separates reproducible engineering from reconstruction of
Vern's method. Read the [Phase 2 protocol](protocol.md) and the unchanged
[Phase 1 calculation contract](../specification.md). The generic knowledge base
defines candidate roles; it does not supply unique node, edge, composite or
projection rules. The three authorized cases constrain the design below;
they do not identify one deterministic construction or selection method.

## Meaning, observation and construction

The [glossary](../../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/glossary.md)
and [level discussion](../../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/levels.md)
distinguish the following. The proposed constructions in the last column are
Abacus engineering hypotheses, not recovered source formulas.

| Family | Source meaning | What a chart can establish | Proposed extension and unidentified detail |
|---|---|---|---|
| Prior extremes / close | Extremes and closing references of a named period | A printed period label and price, or an uncertain axis interval | Keep RTH, full session and overnight distinct; exact feed/session/close convention still needs corroboration |
| YVAH / YPOC / YVAL | Yesterday's value boundaries and point of control | A named prior reference, possibly with another label at the same price | Compare with a declared prior profile; percentage, aggregation, row grid, volume versus TPO and finalization convention remain separate questions |
| HVN | A fuller-volume region | A profile bulge and its annotated center/zone | Segment connected volume regions; a POC alone cannot identify all nodes or their widths |
| LVN | A relatively thin region | A trough or thinner interval between fuller regions | Identify relative minima between accepted regions; minimum contrast and persistence are not recovered |
| HVE | High Volume Edge, a boundary of a fuller region | A labeled border near an accepted region | Derive a candidate boundary from an explicitly defined node; neither VAH/VAL nor a node's center becomes an HVE by renaming |
| Composite balance | A contextual auction spanning named periods | Repeated trade in a region or an explicitly drawn composite profile | Declare exact member sessions before aggregation; automatic start/end and balance discovery remain unidentified |
| PBT | Projected Balance Target, a proposed symmetric completion | A printed destination and any explicitly visible anchors | Transparent projection from causal anchors; anchor choice, center convention and projection family must remain explicit |
| LIS / ordered targets | Scenario divider and destinations | A conditional plan's chosen reference and ordered list | Retain the observed selection as a hypothesis; automated selection remains outside this extension design |

A compound label preserves every role. Equal prices or close levels do not
demonstrate identical constructions or independent confirmations. A volume
distribution cannot establish TPO single prints or a time-based POC. These
limits follow the generic [method model](../../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/method-model.md)
and [unknowns register](../../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/unknowns-and-tensions.md).

## Constraints from the three cases

| Case evidence | What it supports | What the extension must not assume |
|---|---|---|
| [October 1](cases/2026-10-01.md): source ONH/ONL align closely with baseline extremes, while the plan's 6691 VPOC conflicts with an image's 7691 | Keep exact source-price conflicts, compound labels and RTH/full-session alternatives in a reference ledger | Do not silently repair the text, replace its price with the image, or infer that a close numerical match proves the reference period |
| [October 2](cases/2026-10-02.md): source YVAH/YPOC/YVAL differ from baseline by 20/44/16 points; HVE 7785 is neither baseline ON POC nor VAH | Validate the profile backend and session convention before investigating node selection | Do not tune one edge threshold until an incompatible baseline profile happens to match. GAP 7803, ONH 7802.75 and nearby HVE 7804 remain distinct claims |
| [October 5](cases/2026-10-05.md): ON extrema agree, but source Y references differ; a 7767 compound pivot is near both ON POC and prior VAL | Test region-boundary explanations against center/value-area alternatives, retaining all nearby references | Do not identify the pivot's HVE construction from proximity or from the later bullish move |
| October 5's plotted PBT-ETH 7746.75 differs from the plan's 7746, and two declared overnight-range/center alternatives do not reproduce it | Keep projection arithmetic transparent and manual anchors auditable | Do not choose a different center or range after seeing the target, or claim rounded text and plotted axis values are identical |
| Higher PBTs have later-only visibility in selected closing evidence; earlier crops exclude that price domain | Record source visibility bounds and historical timing separately | Absence from a crop is not proof of absence or intraday creation |

The cases justify a source-conflict/reference ledger and an inspectable
candidate laboratory. They do not validate automatic node/edge/anchor discovery.
Source profile settings, composite membership and causal PBT anchors remain
missing. Printed plans also condition choices on VIX/CVD; these inputs are not
measured by the Phase 1 level generator. Later reactions are not selection labels.

## Shared input and availability contract

Every future module must consume a saved, identified distribution or an
explicitly declared set of completed bars. Required inputs are:

- Actual contract, feed and adjustment convention; price tick and units.
- Reference-window IDs and civil New York start/end times. RTH, full futures
  session, overnight prefix and a multi-session composite remain distinct.
- Profile method, row width/origin, volume or TPO measurement, value-area
  settings where used, and the completed-bar cutoff.
- Ordered rows with lower/upper price bounds and nonnegative mass, total mass,
  last included bar, coverage, missing-volume status and overflow status.
- Source/code/settings hashes and any anchor's original observation and
  confirmation timestamps. A feed correction produces a new evidence identity.

Phase 1's distribution is uniform chart-bar volume allocation over inclusive
touched bins. It may be one exploratory backend. Exact traded volume at price
requires a separately identified input; the approximation must not be presented
as that input. Reaggregating 5-minute candles cannot recover observed tick-level
volume allocation. A finer row grid changes quantization, not source resolution.

For a 09:25 pre-open output, all constituent bars must be confirmed with closing
times at or before 09:25. The default 5-minute final interval is 09:20–09:25.
Each anchor must have become identifiable under its declared rule by that same
cutoff. Today's RTH opening price, initial balance and later extrema cannot
enter. A drawing's horizontal start is not its availability time.

Empty/zero-volume profiles, partial windows, missing terminal bars, inconsistent
contracts and unresolved measurement types produce explicit unavailable or
qualified outputs. Unknown status is not a negative detection. Historical
source `available_at=null` remains null even when an engineering reconstruction
can be produced today.

## Module N: exploratory HVN/LVN regions

Purpose: produce several explainable distribution features, independently of
whether Vern selected them. This is candidate generation, not a trade policy.

Required calculations for a future prototype:

1. Normalize row mass by the complete reference profile's total. Preserve the
   original histogram beside any smoothed representation.
2. Apply one globally declared odd-width smoothing policy. A width of one is
   the unsmoothed control. Do not let smoothing invent mass across an excluded
   session, missing-price domain or another contract.
3. Identify contiguous local-maximum plateaus. Record the whole plateau;
   choose a deterministic representative row only for display.
4. Qualify candidate peaks using declared relative-height, prominence and
   minimum-separation rules. Report both rejected and retained peaks with the
   reason for each decision.
5. Expand each retained peak to region bounds using one declared relation to
   surrounding troughs. Record the connected rows and integrated mass.
6. Identify LVN intervals from intervening troughs between qualified regions,
   retaining width and relative depth. Profile-domain endpoints are not
   automatically LVNs.

Mandatory parameters are row grid, smoothing width/padding, plateau tie rule,
relative-height threshold, prominence definition/threshold, trough search
window, region-boundary fraction, minimum peak separation and maximum displayed
regions. A future protocol must choose exact values and policy versions before
evaluation. Three examples cannot identify those defaults as Vern's settings.

If output must be capped, cap presentation deterministically by declared node
mass/peak/tie criteria, record omitted IDs/counts and retain the uncapped
candidate ledger. This cap does not select an LIS or bullish/bearish targets.
Do not silently merge nearby regions, or use later prices to retain a region
that would otherwise fail.

### Unexecuted N1/E1 engineering control

This concrete proposal is unvalidated, unfitted to these cases and unattributed
to Vern. It requires new authorization and a protocol freeze before execution.
Use 16-tick rows, zero-anchored grid, no smoothing and at most 6,000 rows.

N1 detects interior equal-height maximum plateaus with strictly lower adjacent
rows. Representative = lowest-price plateau row. For peak height p, search each
side until the first strictly higher row or domain end; take each search's
minimum. Saddle s = larger minimum; prominence d = p−s. Require p ≥ 0.20 times
global maximum and d ≥ 0.10 times global maximum. Grow contiguous rows from the
plateau while mass ≥ s+0.5d. Rank by height, prominence, then ascending price;
reject representatives less than two rows apart. Keep eight regions, flag
overlap, never merge. Between adjacent disjoint regions in price order, LVN = lowest plateau (lowest-price
tie), requiring mass ≤ 0.25 times the smaller parent peak; maximum seven LVNs.

E1 requires a two-row-wide parent and observed outside neighbors. Qualify each
border when (inside mass−outside mass)/p ≥ 0.10. Emit the shared bin boundary B
as a grid coordinate with uncertainty [B−row/2, B+row/2], not an exact observed
edge; maximum sixteen edges. Domain-truncated edges are unavailable. Retain
rejection reasons and omitted counts; caps never select pivots or targets.

Expected output per region: stable ID; profile/window ID; HVN or LVN candidate
kind; representative row plus full price interval; defining peak/trough rows;
raw/smoothed mass; prominence/contrast; parameters; ready-at time; qualification
flags; and provenance. Persist intervals instead of implying false tick precision.

## Module E: candidate high-volume edges

An edge requires a parent HVN region. Emit its lower and upper candidate edge
intervals from the exact node-boundary rule, retaining the adjacent row masses
and transition direction. Distinguish a steep transition from the boundary of
a broad, shallow shoulder. Do not substitute the parent peak or a cumulative
value-area boundary.

Required parameters add minimum transition contrast/gradient, measurement span,
minimum contiguous accepted-region width, and an explicit rule for whether the
edge is a bin boundary, row center or uncertainty interval. Tick buffers, if
eventually used, are separate output fields and require their own protocol.

Expected output adds parent region ID, lower/upper side, price interval,
transition evidence, cutoff readiness and a candidate-only label. An HVE
confidence number must not imply a calibrated probability. Until construction
is supported, retain a categorical evidence-strength field and its basis.

## Module C: explicit composite references

A first prototype may aggregate a manually declared, ordered list of completed
sessions using a common contract, price grid and measurement method. Record
each member's start/end, readiness, inclusion reason and mass. Sum compatible
rows, then apply the same globally specified N/E policies to the saved composite.

Parameters include exact membership or a fixed session-count rule, RTH versus
full-session scope, row grid and treatment of contract rollover. No current
case may receive a bespoke window merely because it fits a target. Do not
combine back-adjusted history with unadjusted execution/reference prices.

Automatic identification of a balance's first/last session is a different
module. It needs a causal balance definition and more training evidence. A
composite histogram alone does not establish a balance or identify open
positions.

## Module P: transparent PBT projection ledger

Start with explicitly entered or independently evidenced anchors. The ledger
must distinguish these two hypotheses instead of switching between them to fit
a printed target:

| Hypothesis | Required anchors | Calculation | Unidentified decision |
|---|---|---|---|
| P1, reflection about a declared center | Center C and observed edge E | Candidate completion T = 2C − E | Which distribution supplies C; whether C is modal price, midpoint or another center; which edge is causal |
| P2, extension by a declared balance width | Lower boundary L and upper boundary H, L < H | Width W = H − L; upper T = H + W, lower T = L − W | Which bounds delimit balance and why an extension rather than reflection is appropriate |

If C is the midpoint of a complete known range, reflecting one edge produces
the other existing edge. That identity is not an independently discovered
target. If a chart supplies only a PBT price without its causal anchors, many
centers/ranges fit it; mark the construction unidentified.

Required anchor fields: stable anchor ID, price/interval and reading precision,
reference period and measurement, observed-at and confirmed-at times, source
evidence, explicit-source versus analyst-proposed status, and reason for
selection. For interval anchors, propagate bounds through the selected formula;
do not output more precision than the inputs support. Reject inconsistent
bounds and mixed contracts. Preserve alternative fits without selecting the
one that happens to match the target.

Readiness requires every anchor's causal confirmation time to be at or before
the output time. An anchor inferred from the day's eventual high/low or from a
closing-only distribution cannot explain a pre-open PBT. Such a calculation can
be retained only as a retrospective illustration with a separate status.

Expected output: hypothesis ID; anchor IDs and intervals; arithmetic terms;
candidate target interval; earliest ready-at time; unavailable/retrospective
reason; settings identity; and source evidence. Automatic anchor discovery is
not part of this first projection ledger.

For C in [C_low, C_high] and E in [E_low, E_high], P1's target interval is
[2C_low − E_high, 2C_high − E_low]. P2's upper interval is
[2H_low − L_high, 2H_high − L_low], with lower interval
[2L_low − H_high, 2L_high − H_low]. Tick rounding must be a declared global
presentation policy; preserve the unrounded interval. These are uncertainty
bounds, not target probabilities.

Keep `reconstruction_ready_at` separate from `source_historical_available_at`.
The former describes when an explicitly specified calculation could have used
its anchors; the latter retains the source's historical-availability evidence
and may remain null. A reproducible calculation today cannot supply a missing
historical publication timestamp.

## Required tests before any future implementation is accepted

| Area | Test cases and required behavior |
|---|---|
| Distribution integrity | Empty and all-zero input, missing/negative mass, overflow, total conservation, gaps and incompatible contracts; no stale output survives a reset |
| Regions | Single peak, flat distribution, equal plateaus, broad shoulder, double distribution, unequal adjacent peaks, shallow trough and a domain endpoint; tie and rejection reasons deterministic |
| Edges | One parent with two sides, broad shallow border, abrupt drop, grid-boundary price, a POC inside a node and a VA edge elsewhere; centers/VA boundaries cannot be silently labeled HVE |
| Parameters | Identical global settings for every case; retain control and rejected variants. Changing row width/smoothing must be visible in provenance |
| Composite | Same sessions in different input order, partial member, duplicate member, missing session, rollover and changed adjustment; membership and eligibility reproducible |
| Projection | Reflection and one-range extension have distinct identities; midpoint reflection returns the opposite bound; invalid bounds unavailable; interval uncertainty propagated |
| Timing | Replay to cutoff, advance, restart and truncated history; frozen candidate/anchor identities unchanged; a later-confirmed anchor never appears earlier |
| Missing terminal data | ON/RTH coverage requires the expected final included bar; unavailable does not become a false detection |
| Selection boundary | Candidate cap/order does not become a scenario divider or ordered targets; source plan selections remain an observation ledger |

These are future acceptance tests, not checks executed by Phase 2. Native Pine
compilation/replay remains distinct from a translated specification model.

## Readiness decision

| Work item | Current design status | Evidence needed before a stronger claim |
|---|---|---|
| Source-conflict/reference ledger | Engineering-ready; preserve labels, intervals, compound roles, source revisions and competing prices without automatic repair | Better source readings to resolve a conflict. This registry does not create GAP levels or other new level algorithms |
| Profile/window provenance interface | Engineering-ready using Phase 1 coverage conventions | Exact backend/input identities and implementation tests |
| Manual composite membership ledger | Engineering-ready for explicit compatible sessions | Source evidence that the chosen composite corresponds to a relevant auction |
| HVN/LVN candidate prototype | N1 is concrete enough for an authorized experimental prototype after a new freeze; it is unvalidated | Readable distributions and annotations that distinguish a region from a peak and test the unfitted control |
| HVE candidate prototype | E1 is specified for experimental use with N1 parents; source equivalence remains unidentified | Boundary examples, contrast/width evidence and competing VA/node-center explanations |
| Manual-anchor PBT arithmetic | Engineering-ready as named transparent hypotheses | Pre-cutoff anchor evidence before claiming a causal explanation of Vern's PBT |
| Automatic balance/anchor discovery | Requires more training evidence | Causal anchor selection and disconfirming cases; closing-only fits insufficient |
| LIS/pivot and ordered target selection | Deferred, unimplemented | A separately frozen selection study; no rule inferred uniquely from three examples |

No readiness decision here authorizes Phase 3 execution. Unsupported
construction details remain questions instead of defaults attributed to Vern.
Before implementing stronger reconstruction claims, obtain source profile
settings with contract/session identity, readable distributions that constrain
node/edge boundaries, explicit composite members, and PBT anchor examples whose
publication and confirmation times can be established before the relevant
cutoff. The three case studies supply useful counterexamples, not a unique
replacement for those inputs. LIS/pivot and ordered-target automation remain
outside the next candidate-module implementation.
