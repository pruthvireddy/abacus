# GC- Overnight Breakout 15M — Phase 3 protocol

Protocol `3.0.0`. The October 13, 2026 user instruction explicitly authorizes
implementation, historical backtests, verification, sealed evidence, publication
and production deployment within the existing study. The exact instruction is
retained with the execution freeze. [Settings](config-phase3.json) contain every
threshold, timing convention, control, selection and multiplicity family.
Freeze executed source/settings/input identities before policy outcomes. Read
development/validation first, independently verify, freeze selection, then run
later assessment without retuning. Previously published Phase 1, Phase 2 and
Study 21 history is exposed; chronological assessment is not a pristine holdout.

## Parents and cloud

The primary parent is completed Phase 1 `20261013T142537Z_phase1_gc_ob15m_v1`,
protocol `1.0.0`, primary one-tick standardized one-GC execution. Pin manifest,
settings, selected unadjusted same-contract inputs, eligibility, order/fill/trade
ledgers, metrics, checks and public attribution before outcomes. Reconcile the
parent independently; no original numbers, entries, protection or exits change.
Phase 2 `20261013T190208Z_phase2_gc_ob15m_v2` selected no replacement, so there
is no Phase 2 trading replication parent. Its saved midpoint/protected-boundary
events provide descriptive cloud context only. No cloud/Phase 2 cross-product.

Reuse the byte-verified `same_contract_ema_cloud` 1.1.0 public loader: five-minute
first-close-seeded EMA20/50, alpha 2/(length+1), Wilder ATR14, 250 usable
observations, contract/invalid/unknown-gap resets, scheduled-closure preservation
and modeled availability at exclusive candle completion. Do not rebuild its
release or reset at day/year/evaluation boundaries. EMA ordering equality is
neutral; the user's green visual equality does not make it bullish. The source's
slow-touch marker, 2.40-point width gate, one-per-pullback and cooldown settings
are not inherited policy filters. Study 21's different 2.0-point rule/findings
are not breakout evidence. Lower-timeframe last-intrabar chart display disables
those source touch signals; these policies use a dedicated confirmed five-minute
stream. Formula/byte agreement does not establish native TradingView continuous
history parity or actual feed/cancellation latency.

Latest cloud means the latest **expected** completed same-contract slot.
Missing/invalid/warmup cloud is unknown; do not substitute an older valid row.
Slopes are EMA[k] minus EMA[k−3], requiring four adjacent expected usable
observations (three changes). Known scheduled closures preserve EMA state;
unknown expected omissions break confirmations. Indicators remain raw points.

## Causal decisions and ordering

Keep parent's fixed GMT+3 range [00:00,07:00), trading [07:00,20:00), confirmed
15-minute decisions, boundary-anchored initial one-percent stop and surviving
original-entry-candle reset from actual slipped fill. Evening market-first
opening convention, one-minute authored OHLC path, inherited fees/slippage,
contract barriers and execution censoring remain in effect.

Original order-decision snapshots retain the actual first submission and the
complete usable 15-minute original-source recalculation/update closes while
flat/unconsumed before the unfiltered first boundary event. The compact parent
ledger omits unchanged resubmissions; reconstructed source-call updates are
explicitly labeled and checked against source/state. A gate holds until the
next such update; no five-minute refresh variant. A separate entry snapshot
uses cloud available at the execution minute opening/lower bound. It cannot
retroactively change an earlier order. An unknown entry gate abstains by rule
and is counted separately from missing fill/P&L evidence.

For G1/G2, a causal virtual unfiltered boundary OCA monitor on the inherited
one-minute path fixes the original first-side episode. A blocked first event
consumes the opportunity and cancels the other side; never quietly enter a
later opposite breakout. Preserve unresolved same-candle ordering/cancellation
as unknown rather than manufacturing an admitted same-price fill. This is an
authored cancellation approximation with explicit native-latency limitations.
The first submission tied to the shadow opening inherits the parent initial
availability/opening convention. A later update tied to the shadow execution
minute opening that would change admission versus its preceding standing gate
preserves unknown admission/cancellation and both possible branches. Unchanged
admission is unaffected and retains a tie flag. Tied candidate snapshots remain
in evidence; do not discard them to choose a favorable standing gate.
G1 requires directional EMA ordering and last completed five-minute close
strictly beyond the favorable edge. G2 also requires both three-change slopes
with that direction. Equality fails the positive gate.

Monitor only full five-minute candles whose opening is at or after the original
fill's conservative upper timestamp bound. At a contact opening freeze prior
available levels; confirm only at that contact close, execute next eligible
opening before cutoff. Unknown cloud while open makes no new EMA action and
preserves original protection. Missing execution prices censor actions/outcomes.

## Independent adds and exits

A20/A50 are independent. A strict full post-entry departure beyond the prior
entire cloud arms the setup; a separate later first penetration of the selected
EMA consumes its entire episode attempt, including rejected confirmation,
unknown confirmation, liquidation profit or risk. Fast-only contact does not
consume the slow setup. Unknown prior contact prefix makes the first attempt
unknown; no better later touch is selected. Require strict close back on the
frozen level's trade side, current aligned ordering, original still open, and
positive estimated net liquidation after both commissions and adverse exit
slippage. Do not average into losers. A pending add is canceled when a queued
parent opening exit or opening gap-stop makes the parent flat before release.
An already-filled add survives a later parent exit under its own protection.
Retain gaps and unresolved simultaneous branches; never delete a bad fill.
The add's signal-close one-percent initial stop resets only at its own surviving
five-minute entry candle close; parent retains its original fifteen-minute reset.
Both use the common evening opening and no target.

X1 freezes the prior adverse edge at the first full post-entry close beyond it.
A second adjacent expected usable close beyond that **same** edge queues next-
opening exit. Recovery, equality and unknown slots reset. X2 requires adjacent
full post-entry ordering observations aligned/neutral then strictly opposed;
initial opposition alone is not a fresh cross. Apply both to winners and losers
without consulting eventual parent loss. Original protection stays active until
actual exit; inherited market-first opening priority records competing stops.
Measure loss saved and winner profit surrendered, post-exit favorable paths,
time saved, paired effects and drawdown.

T50 is exploratory, separate from core selection. At confirmed monitoring
close propose one tick beyond the prior EMA50: floor then minus tick for long,
ceil then plus tick for short. Activate only prospectively; ratchet tighter,
preserve tighter original stops, and never loosen at a source stop reset. If
already breached at decision, queue a next-opening market exit, not a historical
stop fill. Missing cloud adds no action. Preserve gap and stop competition.

## Capital, populations and estimands

Source account is frozen $10,000, ten-times notional cap, five-percent margin,
whole GC contracts, one-percent start-of-day-equity daily budget, half reserved
for original and half for one add. No replenishment, fractions or third leg.
Compare full-budget parent, half-budget parent alone, and half/half overlay.
Core A20/A50 effect is financed overlay minus half-parent alone per original
episode. Known quantity skips are zero; unknown capital/price outcomes stay
null. Do not use a standardized hypothetical open position as an actual funded
add opportunity. Separate source-account signals from conditional one-contract
support landmarks. A labeled **unfunded** one-original-plus-one-add diagnostic
may compare one-/two-contract parents; its extra exposure is not equal-risk
entry quality or an assumed increase in account capital. Retain original/add/
combined costs, unused reserve, peak notional, concurrent planned stop risk,
closed/floating drawdown, margin/quantity failures and gap overshoots.

G1/G2/X1/X2 core effects are one-GC net policy minus unchanged one-GC parent.
The six contrasts have an aligned common known mask and individual complete-
pair sensitivities. They do not share a universal profitability ranking because
controls/exposure differ. Preserve all 880 accepted original episodes including
17 censored, and the complete inherited eligibility/unknown/no-trade roster.
Known abstention is zero; missing execution remains null. Never select episodes
retrospectively using eventual cloud contacts or parent outcome.

## Conditional context and bounded diagnostics

The one-original/one-added-GC diagnostic has its own three-way complete mask
with one-GC and two-GC parent controls. Report both control differences and
separately observed-pair sensitivities per original-entry cohort; apply no
core selection or confidence-family claim to this larger-exposure diagnostic.
For new signed protective-risk/R metadata, prices within 1e-8 instrument ticks
of a canonical tick share that tick identity. Preserve actual raw/slipped
prices, order/fill paths and raw quantity-sizing distances. This prevents
binary noise at equal entry/stop prices creating a positive risk denominator;
it does not alter the saved Phase1 control statistics or a trade decision.

Store original order decision and separate actual-entry snapshots. Profiles
use alignment, above/inside/below price, directional three-change slopes,
ordering duration, raw/ATR width, directional distance from favorable edge,
expansion/contraction and range confluence. Fixed ATR-width bins start at
0/.25/.5/1/2; signed distance bins negative/0/.5/1/2; duration bins 1/4/13/37
usable bars, with left-censored starts distinct. No fitted confidence score or
calibrated probability. Confluence is each EMA within inclusive 0.10 positive
ATR14 of known H/L/M. Report missing/warmup support, distinct episodes, costs,
denominators, uncertainty and annual/session stability.
Original order/entry bins also report inherited completed-parent MFE, MAE and
holding-time means from the pinned Phase1 rows. These describe subsequent
whole parent paths from actual entry. Leave those fields unavailable for
later EMA/open-position landmarks, where whole-parent excursions could
include movement before the event; use the source-candle-excluded forward
diagnostics for post-event paths instead.

Eligible open-position landmarks are conditional on survival to the decision;
they cannot establish whole-strategy improvement. Retest diagnostics separately
rearm after a new later full departure beyond the prior cloud after a consumed
contact, independently per EMA. Contact ordinal first/second/third-or-more is
diagnostic and never grants another add. Record touch, conservatively tick-
rounded one-tick breach, strict close break/hold, ordering flip and a separate
later close reclaim of the **same frozen contact level** through broker cutoff.
Recovery may occur after parent exit; label it price recovery rather than trade
profit. Unresolved exposure remains unknown and known observed events persist.
The contact-close ordering flip means the prior available valid cloud was
aligned or neutral and the current confirmed cloud is strictly opposed; an
unavailable side makes this descriptive event unknown. It is not an X2 signal
unless X2's separate full post-fill adjacency rules also qualify. Stratify
hold, tick breach, closing break, later frozen-level reclaim and this flip by
the selected prior EMA's H/L/M confluence (yes/no/unknown), with event-year,
event-session and original-side cohorts. Reclaim denominators contain known
tick-breached contacts only; other events use the full contact cohort.
From event close measure signed close movement and MFE/MAE over exact 5/15/30/60
wall-clock minutes, excluding source candle. Missing or cutoff-crossing horizons
are censored; these are price paths, not assumed take-profit or realized returns.
Phase 2 context uses only cloud available at its previously saved event time,
with minute timing bounds/availability limits retained.

## Chronology, statistics and presentation

Development 2018–2020, validation 2021–2023, later 2024–2025, available partial
2026 replication. All policies frozen and isolated; no combined policy this run.
Standalone advancement requires positive validation paired mean **and** positive
99.166667% marginal lower bound, at least 100 completed executable policy trades
across two validation years; adds also require 100 actually financed add fills
in two years. Select at most one gate and one exit; ties prefer G1 and X1.
Adds are separate financed controls; secondary diagnostics cannot qualify core
selection. Assess every prespecified rule later without retuning and retain
negative/sparse/inconclusive outcomes.

Episode-aligned Monday calendar four-week block resampling uses 10,000 draws,
seed 230015, one/eight-week sensitivities, pointwise 95% and 99.166667% marginal
intervals for six declared contrasts. Preserve calendar spacing, censor masks,
no-fill zeros, repeated events and all within-episode legs. Correction applies
within the stated cohort, not all profile/year/session/side searches at once.
Conditional empirical profiles remain exploratory with their own support.

America/New_York DST windows remain Asia [20:00,02:00), London [02:00,09:00),
New York [09:30,16:00), Outside otherwise. Paired cohorts use original actual
entry; cloud statistics use decision/event; added legs use actual add fill.
Save overall/year/session/year×session/long-short and original→event→add
transitions. Unfilled adds have no invented session. Whole trade P&L stays in
its entry cohort and within-year closed drawdown differs from full-history
drawdown. Partial years, empty cohorts and unknowns are explicit.

Prepare saved report JSON, exact source-cell bindings, CSVs, figures and
independent verification **before** sealing a unique run. Retain sources,
settings, parent/input pins, dirty/code/environment snapshots, exact commands,
exclusions and all ledgers. Native replay and broader workspace prerequisites
have honest separate scopes. Publish seven EMA Cloud Phase 3 conditions with
Summary/Year-wise/Sessions, methods/risk and baseline links. Illustrative guides
are labeled; empirical success/failure and saved-loss/cut-winner cases trace to
pinned ledgers. Narada only selects saved rows, never computes statistics.
Preserve earlier study/report identities and release bytes. Verify local,
protected preview where accessible, staged and anonymous production with actual
in-app browser findings, plus the exact static release gates. No plan/preview-
only stopping point is authorized.

Before the first support departure, any unavailable full post-fill expected candle may hide an earlier departure/contact. A20/A50 conservatively consume an unknown attempt and abstain for that episode; later observed diagnostic contacts retain unknown contact order. Original protection stays active. Whole-GC sizing inherits the raw submitted boundary-to-stop risk distance for the original and uses the analogous raw signal-close-to-stop distance for the add. Fees, slippage and gaps are disclosed as risk overshoots rather than silently changing the parent sizing convention.

Cloud-contact path diagnostics define a full raw-EMA adverse one-tick displacement. The tick-grid threshold is floor(frozen EMA / 0.1) × 0.1 − 0.1 for a long, and ceil(frozen EMA / 0.1) × 0.1 + 0.1 for a short. It is at least one raw tick beyond an off-grid EMA. Touch and confirmed hold/break still compare with the unrounded frozen raw EMA; these diagnostics are not retrospective stop fills. This convention was finalized before Phase3 historical scoring.
