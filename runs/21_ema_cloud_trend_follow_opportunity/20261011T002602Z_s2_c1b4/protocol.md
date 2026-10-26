# Executed Stage 2 protocol

Version `0.1.0-stage2.0`, defined before Stage 2 historical scoring. The user's
Stage 2 instruction authorizes implementation, tests, 2018–2020 execution,
independent reconciliation, private report preparation and immutable sealing.
The plan remains version 0.1.0. Stage 3 and public publication remain outside scope.

## Inherited authority and exact slow parity

The authoritative slow baseline is
`20261010T221954Z_s1_8c6e_r3`, protocol `0.1.0-stage1.2`. Its handoff scientific
hashes, all declared local artifacts, external ledgers and the immutable
`same_contract_ema_cloud` 1.0.0 delivery are verified before use. Delivery manifest
SHA-256 is `59010a558b4e727dbfaa37a64b4a209590288f23744127ab98747cd27ff56d44`.
No feature release is rebuilt. Original producer source, corrected canonical
source and post-seal verifier/caption repairs remain separately identified.

The unchanged numerical mapping, slow event, forward-outcome and statistical
kernels are retained and matched against the baseline source snapshot. Slow
technical fields, accepted IDs, state, suppressions, input/reference identities,
every horizon/outcome/censor value, summaries, quantiles, stability and original
uncertainty/3m–5m comparison estimands must reproduce the sealed baseline.
The explicit scientific tolerance is zero; only declared Stage 2 wrapper fields
and new membership/shared-episode metadata are excluded. Baseline table row keys
and values are regenerated in a separate parity directory. Headline counts are
insufficient. Complete slow parity is a gate before fast outcome scoring and
interpretation. Acceptance, slow evidence and final evidence have separate
immutable phase manifests, so recorded comparison pins do not become stale.

## Shared inputs and independent streams

ES/GC/NQ × 3m/5m candles retain the 5m EMA20/50 cloud, ATR14, first-close EMA
seeds, fourteen-TR Wilder seed, 250-observation warmup and same-contract reset
rules. The fixed inclusive widths are ES 2.4, GC 2 and NQ 10 raw points, with
epsilon `1e-10*max(1,abs(threshold))`. Both directions are enabled, cooldown is
zero, and each selected EMA permits one accepted signal per pullback.

Slow selects EMA50 and fast selects EMA20. Each has independent arm/consume
state, never derived by filtering the other's accepted events. A valid full
strict departure outside the entire cloud arms the corresponding direction;
acceptance uses pre-bar state, inclusive selected-EMA range touch and width.
Any selected-EMA penetration consumes that stream, including rejected touches
and gaps through it. A fresh full-cloud departure rearms. Invalid features/data,
equality, direction changes and contract/reset boundaries clear its state.
Neither stream, path completion nor retrospective matching changes the other.

5m candles use their completed current close-derived cloud. 3m candles freeze
the latest scheduled 5m cloud completed at their open; the invalid latest source
is retained and makes features undefined immediately. Contract identity must
agree; stale features cannot cross missing slots or rolls. Input quality,
conservative uncertified calendars, known closures and the coverage roster are
identical to Stage 1. Eligibility is `usable AND feature_valid`; All support
retains undefined direction, while Buy/Sell support is conditional on direction.

## Geometry, accepted membership, union and shared episodes

Geometry is independent of state: fast-only, slow-only, both, neither, or
undefined when required candle/features are unavailable. Finite equal EMAs can
have defined geometry, while equality prevents a directional signal. Accepted
membership separately records both independent decisions, IDs and reasons.
A geometric dual touch need not be accepted by both streams.

Union identity is product, interval, direction and signal-open timestamp. Dual
accepted same-bar events count once and retain both IDs; different times remain
separate. A deterministic slow-preferred representative is retained for dual
accepted rows, with both source IDs and exact same-bar equality. Same-bar
reference close, ATR, direction and every path outcome must
agree exactly. Union evidence is an observational diagnostic.

Shared geometric episodes use a separate ID and never replace inherited slow
`episode_id`. A valid first full-cloud departure starts an episode without a
width gateway. Consecutive departures retain the ID. After a non-departure bar,
the next departure closes the old episode and starts a new one. Quality,
contract, direction and feature resets terminate before their reset bar.
The first accepted fast and first accepted slow in full causal history define
the pair; a warmup counterpart remains identified and is never replaced merely
to obtain a scoped/completed pair. Forward-path episode differences require both
selected events in development and complete at the requested horizon.
Descriptive signal-time and reference-price input differences require both
selected events in development, with no future-completion filter.

Same-bar, fast-before-slow, slow-before-fast and unpaired cases remain explicit.
For a first fast event in development, retain same-bar slow geometry separately
from strictly later slow geometry and strictly later accepted slow signal.
Observed contact is true. Absence is false only when a fully observed new
departure closes the episode. Missing/reset/endpoint interruptions with no
observed contact are null/unresolved. Warmup-first descriptors are null with an
outside-scope reason; no retrospective warmup result is calculated. All such
labels are retrospective descriptors and never causal entry filters.

## Outcomes, summaries and comparison family

Only NY signal-open dates in 2018–2020 receive outcomes, and all paths end by
`2021-01-01T00:00:00-05:00`; 2017 is causal warmup. Reference is unadjusted signal
close, entry candle excluded. The unchanged Stage 1 scheduled-slot scorer
preserves overlap, nulls, censor precedence, attainment times, opposite-event
independence, signs and MFE/MAE tie tolerance. Horizons are 5/10/15/20/30/50/100,
plus H12 for 5m. H15 is primary: 45 active minutes for 3m, 75 for 5m.

Branch scorecards retain All/Buy/Sell, raw product points and ATR normalization,
event weighting and contributing-session balance, exact linear quantiles and
deciles, annual/session/hour/week/month stability and missingness qualifications.
Common support is the shared eligible roster, not accepted-timestamp intersection.
Equal-active views are 3m H20 vs 5m H12 (60 minutes) and 3m H50 vs 5m H30 (150),
with uninterrupted-path views and actual elapsed time kept separate.

The primary family has exactly six pooled All/H15/raw-point/all-support
event-weighted mean terminal contrasts: fast minus slow, one per product/interval.
Both means share calendar blocks, without event-level matching. Calendar weeks
are the exact 157 Monday weeks 2018-01-01 through 2020-12-28. Circular moving
blocks use 10,000 replicates, seed 20261010, four-week primary and one/eight-week
sensitivities, identical weights across branches and cells. Signal-open event
weeks and intact contributing-session trading-date weeks are unchanged.
Absent means remain undefined, with undefined contrast draws counted.

Pointwise percentile intervals have 95% coverage. The six primary Bonferroni
intervals use exact tails `0.05/12` and `1-0.05/12`, corresponding to marginal
coverage `1-0.05/6 = 99.1666667%`. Only this family receives that adjustment.
Side/ATR/session/other-horizon comparisons are secondary descriptions. New
branch intervals cover H15 and matched-duration views, All/Buy/Sell,
points/ATR, event/session weights and all/uninterrupted support; other horizons
and same-session comparisons retain descriptive point estimates. Original
within-branch Stage 1 uncertainty conventions remain available and parity-tested.
Sparse support means fewer than 100 complete events or 30 contributing sessions.

## Prespecified examples, reporting and sealing

Before scores, freeze six H15/All example classes per cell: maximum completed
MAE across both branches; earliest rejected directed candidate; earliest H15
censored event; earliest scoped-first-fast unresolved episode; earliest scoped
first-event same-bar pair; earliest scoped first-event differing-time pair.
An unresolved example requires a scoped first fast event, no same-bar slow
geometry and an undefined strictly-later slow-contact descriptor.
Ties use timestamp and stable IDs (rejected also branch/slot; pairs both IDs and
shared ID). Unavailable classes remain explicit, without replacements.
Each window is signal slots −10 through +15, displayed only in NY2018–2020.
Pair examples use two separately capped windows with explicit omitted gaps,
at most 52 rows before deduplication. Exact selector definitions are in config.

Save S2-T00–T06 and geometry/membership T07, branch contrasts/uncertainty T08,
retrospective first-event episodes T09 and union/overlap T10. Every numerical
claim, public cell, figure and selected original-string CSV is bound to saved
evidence. Cross-run attribution is explicit in private source bindings; Narada
saved-artifact references remain confined to their source run. Offline reports,
dated advice, six bounded raster figures, four selected downloads and private
Narada 1.1 content are reconciled before immutable sealing.

Source/config/protocol, commands, environment/uv.lock, actual numerical results,
input/parity/scientific/publication checks and artifact bytes are retained.
Declared-local integrity, external-byte verification and scientific validity are
separate. Failed diagnostic attempts are preserved. No raw reconstruction,
native TradingView, original vendor/mapping arrival, annual-calendar certification
or off-device backup qualification is promoted by these checks.

No 2010–2017 or 2021+ outcomes, optimization, combined position policy, fills,
stops/targets/profitability, public staging/catalog change or deployment occurs.
Later periods remain reserved for Stage 3; prior Abacus market-history exposure
prevents calling them pristine holdouts. No favorable side/hour/horizon is selected.
