# Frozen feature reconstruction contract 1.0.0

Prepared 2026-09-27 before any study outcome examination. This freezes reusable
feature arithmetic and availability, independently of the unresolved setup 1
entry definition. The three-setup primary comparison family remains unfrozen.

Source: [the unchanged Pine script](reference/vp_hvn_levels_dev.pine), SHA-256
`6fb8254d661c41e8a867953e608886bf367ee3a759a110eab41f2469d373e8ee`.
Request: [nq_causal_vp_hvn 1.0.0](../../requests/inbox/nq_causal_vp_hvn__1.0.0.yaml).

## Arithmetic and coordinates

Decode the source through Bhishma's public continuous loader. Validate exact
fixed-point quarter-tick alignment before recovering exact binary quarter-point
prices; this prevents conversion noise from changing a floor-based row index.
Primary coordinates are actual selected-contract prices. Preserve final adjusted
bars as a separately labeled retrospective sensitivity, translated back to the
current contract coordinates in the snapshot; all fills must use raw prices.
Verify timestamp, symbol, instrument, roll, mapping, volume, and adjustment
lineage between variants by identity, independently of their physical row order.

Main profiles use sequential volume addition to every touched absolute four-point
row, including the row at an exact upper boundary. First maximum wins POC;
equal adjacent volumes expand upward first. Report lower row coordinates for
POC, VAL, and VAH. VA mass is 70%. Missing volume contributes zero. Source init
clears bins but retains reported levels; null or stale initial levels are never
silently represented as a new complete profile.

PDH/PDL use full 18:00–17:00 futures sessions. Early source years contain
17:00–18:00 observations: Pine's weekly profile includes those chart bars,
while PDH/PDL and HVN do not. Retain and count these separately, without
changing the source's clock scope. The RTH profile is 09:30–16:00;
Dates containing only out-of-futures observations do not create an HVN session
or roll PDH/PDL forward; they still update weekly VP and the observed ON in/out
transition, as the source does. Retain them in the quality ledger.
after RTH the displayed prior-RTH filter uses that newly completed profile.
Developing RTH is hidden when the new 18:00 futures session begins and contributes
no Asia filter. Overnight is 18:00–09:30. Reset overnight only on the source's
in/out transition; a missing entire intervening period is retained and flagged.

Weekly profiles reset on Monday trading dates (Sunday 18:00 New York for normal
Globex weeks). This follows exchange overnight-session semantics documented by
[TradingView](https://www.tradingview.com/pine-script-docs/concepts/time/).
DST, Sunday evenings, and year boundaries are tested. No independent TradingView
NQ feed snapshot has been supplied: exact external-feed weekly boundary parity
is **not certified**, and that limitation must accompany the final report.

HVN retains ten completed observed futures sessions plus the developing session.
For unique one-minute bars this is at most 15,180 entries; the source's 90,000
entry eviction cap cannot bind. Keep mixed contracts and missing minutes in the
literal state and expose exclusions; never shorten the history to obtain a node.
The low-anchored one-point grid has the source's adaptive 3,000-row cap. Allocate
volume sequentially, then average three centered rows with edge truncation.
Use 20% peak height, ±5-row neighborhood with lower-price equal-peak preference,
10% prominence against the higher side trough, 60% prominence expansion,
and a two-point width cap, even for an adaptive row wider than that cap.

Selection first removes price-containing and reference-colliding candidates.
Only eligible candidates compete by strength; suppress bands separated by at
most two points, then sort by midpoint distance and descending strength, then
apply two-point zone clearance and two-per-side quotas. Equality collides.
Equal strength suppression uses lower candidate order deterministically;
Pine's sort-indices tie stability is not externally certified.

## Historical availability

Replace the last-bar/last-confirmed-history gate with a sequential historical
replay. Seed at the first observed futures-minute close, then rebuild at the
first close at least 15 elapsed minutes later. A new futures session forces a
new seed. Save 18:00–00:00 snapshots; reconstruct reference state from **all**
source minutes. Outside-window candidate rebuilds cannot change evening caches
after the new session's mandatory seed and are not exported.

At minute t save profiles, candidates and selection from completed bars through
t−1, using its known close for selection. Then incorporate minute t and save
post-bar overnight values and selection. The current row's OHLCV, symbol and
source-quality observations are separately identified; they are not pre-bar
features. Candidate availability is the actual rebuild close, never a box's
left drawing coordinate. Retain bounds, strength, ranks, candidate IDs and all
filter decisions for raw and adjusted frames. Match overlapping bands with
centers within two points; flag splits/merges and preserve their prior lineage.

## Quality and acceptance

No forward filling. Strict overnight completeness is 18:00 through the consumed
signal, independent of later minutes. HVN and enabled-reference completeness
are separate. Full reference sessions expect 1,380 bars, or 1,365 before
2021-06-28 to allow the known 16:15–16:30 equity pause. Early closures, holidays
and missing minutes receive incomplete flags rather than invented observations.
Prior-week strict completeness requires all five normal sessions. These strict
flags may substantially reduce usable HVN history and require an available-bar
sensitivity when the study is executed. Never inherit another study's day filter.

Source degraded-day flags propagate across consumed overnight, weekly, prior-RTH,
PDH/PDL and HVN histories. Roll contamination is determined from the contracts
actually in each reference, independently for overnight and HVN consumers.
Do not interpret final mapping or condition reports as certified live knowledge.

Require pinned full hashes and raw/adjusted lineage checks, synthetic scalar/native
arithmetic agreement without fast-math, bounded pilot timing/mass/selection checks,
and deterministic replay. The C++ accelerator is compiled from saved source with
compiler/version/command recorded; it adds no Python dependency or numerical rule.
Validate a full staged release before publication. Never overwrite an existing
release or a completed research run. No study outcome execution is authorized
by this feature-only contract while setup 1 remains unresolved.
