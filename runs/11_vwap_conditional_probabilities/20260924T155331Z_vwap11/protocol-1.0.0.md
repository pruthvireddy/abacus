# VWAP conditional probabilities executable protocol 1.0.0

Frozen 2026-09-24 after corrected feature-only gate
`20260924T155331Z_vwap11` and before any future one-minute target outcome was
opened. The JSON companion is the exact executable configuration. An earlier
feature-only gate is retained in the notes; it exposed a path-context warm-up
mismatch and produced no outcomes.

## Inputs, populations, and availability

Use the pinned `session_anchored_vwap__1.0.0` two-minute release as primary,
the independent five-minute calculation as a correlated sensitivity, and the
matching `volume_lead_unadjusted_v1` one-minute source for future paths. Verify
all manifest and consumed partition hashes. Translate adjusted feature levels
into the session's unadjusted contract coordinates by subtracting the fixed
`price_adjustment × 1e-9`. A changed contract, instrument, adjustment, anchor,
or a missing source minute makes the affected outcome unavailable.

Globex is the day VWAP. A/B use Globex and each local anchor only in its exact
Asia, London, or NY membership window. The five-minute A/B sensitivity uses
Globex; the five-minute corridor sensitivity retains the three local sessions.
All anchors require 30 elapsed minutes, positive sigma, and a valid VWAP. The
additional 30-minute residence/slope context is unavailable until anchor age 60
minutes. Earlier eligible events receive geometry-only estimates, never a
manufactured state.

The signal is observable at the completed output bar's exclusive close. Future
observation begins with the unadjusted one-minute bar opening at that timestamp;
the signal bar cannot satisfy a future target. Require all 30 future minutes at
signal time. Complete-day eligibility is retrospective, not a live predictor.

## A/B departure episodes and checkpoints

A fresh departure is the first mature completed close with
`abs(close − VWAP) >= max(sigma, 4 ticks)` after an observed armed close inside
that threshold. An already-away first mature observation is excluded because
its departure time is unknown. The side and departure VWAP/sigma are recorded.

Episode survival means that no later output bar has intersected the one-tick
zone around the latest VWAP known before that bar opened. A complete gap through
the zone, a completed-bar reference overtake, contract/anchor/window change, or
window end also terminates the episode but is not mislabeled an exact contact.
A later inside-threshold completed close rearms; the terminating bar cannot
start a new episode.

Eligible checkpoints are completed bars whose New York clock minute is divisible
by ten, strictly after departure, with 30 minutes remaining. Repeated checkpoints
retain the same episode ID. Survival uses causal evolving VWAP, while outcomes
below deliberately use different, explicitly named references.

### Question A

Primary: contact the checkpoint-frozen VWAP rounded half-up to a tick, within
its inclusive ±1-tick zone, during the next 30 elapsed minutes. Secondary:
frozen contact by the observation-window end, and causal evolving-VWAP contact
over both deadlines. A gap wholly through a zone is not an exact contact; it is
flagged and later exact contact can still occur. Report evolving contact without
frozen contact as the reference-movement contribution.

### Question B

From the same checkpoint and next one-minute open, race the frozen return zone
against a further move away equal to `ceil(0.5 × checkpoint sigma / tick)`
ticks from the checkpoint close. The fixed extension point is rounded outward.
Retain return first, extension first, neither, and same-minute ambiguous in the
full denominator. An opening gap beyond a target resolves that target first and
is separately flagged. Retain 0.25- and 1.0-sigma extension sensitivities.

Report actual return and extension distances in points, ticks, and sigma units.
Fifty percent is not a neutral benchmark because the barriers are unequal.
Report full-horizon movements separately from movement before resolution and
from target-conditional distributions.

## C: day/session VWAP corridor

Use the release's published completed-close local-session VWAP cross. Both
Globex and local anchors must be mature and valid. After the cross, the close
must lie strictly between the rounded one-tick zones. The references must be
separated by at least **8 ticks and 0.25 current day sigma**. This feature-only
rule leaves four ticks of interior room after both zones and retained 15,078
two-minute events across 2,962 product-sessions, with at least 953 events in
every product × local-session cell before any outcomes were seen.

Freeze both destination zones. Race day VWAP against session-VWAP reclaim for
30 minutes, mirrored when day VWAP is above. Preserve day first, session first,
neither, same-minute ambiguous, opening gaps, and unavailable outcomes. Each
accepted event suppresses all subsequent qualifying crosses in the same local
anchor for a fixed 30 minutes, irrespective of its future path. Report causal
evolving-reference contact separately.

At 10 and 20 minutes, among original frozen-target races still unresolved,
measure the remaining race to the original event deadline directly. These are
updated conditional populations, not reused event-time frequencies.

## Context, prediction comparison, and uncertainty

Question A's baseline uses product, anchor, current distance, clock, prior-only
ATR regime, anchor age, and time remaining. Question B replaces current distance
with the return-distance share of total two-barrier distance. Added A/B context
is elapsed survival time, the frozen residence/slope class, and maximum observed
excursion. Question C's baseline uses distances through corridor position and
width plus product/session, clock, prior ATR, and time remaining; added context
is the past-only slope-agreement, prior-hold, and widening/narrowing class.

Use a development-only, Dirichlet-smoothed conditional estimator. A specific
added-context cell needs 100 development observations; otherwise its prediction
falls back to the geometry baseline. Baseline cells use the same support floor
and documented hierarchical backoff. Apply frozen bins unchanged to 2024 and
2025–2026. Report multiclass Brier score, calibration, specific-cell coverage,
and score differences. These chronological periods are diagnostics, not pristine
holdouts.

Raw intervals and Brier-difference intervals resample whole shared ISO weeks 400
times with seed 1111, preserving products, anchors, timeframes, episodes, and
checkpoints together. Always report rows, distinct episodes, product-sessions,
and weeks. ES, NQ, and GC are primary separate estimates. No familywise
superiority claim is attempted. All results describe conditional price paths,
not a trading win rate, entry system, fill model, or profitability.
