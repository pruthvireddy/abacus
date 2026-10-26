# Asia session VP levels study

Study `14_asia_session_vp_levels` · NQ futures · Frozen protocol 1.0.0
Prepared 2026-09-27 and frozen 2026-09-29 after the user's setup 1 answers.
Implementation and execution are authorized. Feature reconstruction and synthetic
tests passed before the freeze; no real study signal cohort or trade outcome had
been calculated when this protocol was frozen.

## 1. Question and scope

During 20:00–00:00 America/New_York, what favorable and adverse price paths
follow three proposed setups based on the supplied **VP-HVN Levels Dev** indicator?

1. Return to developing overnight POC after an excursion outside value.
2. Continuation after a breakout and retest of developing overnight VAH/VAL.
3. Fade of a composite HVN zone selected by the indicator's filters.

Evaluate long and short cases separately and together. Start with NQ one-minute
bars. ES and GC are later extensions, requiring separate protocols and evidence.
The user's conviction on setup 1 is a hypothesis, not a reason to change its
definitions or favor positive results. This study first measures paths; it does
not establish an executable or profitable strategy from excursion extrema.

**Confirmed interpretation:** setup 1 enters at POC to fade the return leg.
The user separately confirmed buying after the upper excursion and selling
short after the lower excursion. Value-area re-entry targeting POC is a
different, opposite-direction hypothesis outside this execution.

## 2. Clock, session, and sample

- Build overnight profiles from 18:00, even though entries start at 20:00.
  The profile continues developing; do not freeze it at 20:00 or use its final
  09:30 values retrospectively.
- Entry window is `[20:00, 00:00)` New York wall time. A signal at 23:59 close
  whose next open is 00:00 does not qualify. Signals are assigned to the futures
  session date, with the preceding evening date also retained.
- Pre-20:00 breakouts can arm a setup; its actual trigger and entry must occur
  in the entry window. Report pre-20:00 versus post-20:00 origins separately.
- Retain Sunday evening openings, labeled by the following Monday's futures
  session. No invented Friday/Saturday trading sessions.
- Primary fixed horizons are 5, 15, 30, 60, and 120 elapsed minutes, with
  **30 minutes prespecified as primary**. A horizon is eligible only if its
  complete path ends by midnight. Give each horizon its own denominator.
- Also report every otherwise valid entry through midnight, with variable
  holding length shown explicitly. These results are not pooled with fixed
  horizons. Entries late in the evening are administratively censored for
  longer horizons, not counted as losses or silently removed from all tables.
- Confirmed NQ source coverage is 2010-06-06 18:00 NY through 2026-09-18 16:59
  NY, from Parquet metadata; signal eligibility has not yet been audited.
  2010 is partial history and 2026 is YTD.
- Proposed chronological partitions: 2010–2019 historical context, 2020–2023
  development, 2024–2025 validation, and 2026 YTD a final chronological check.
  Freeze definitions before viewing study-specific outcomes. Disclose prior
  familiarity with these years; do not claim the market history is pristine.
  Supply a full-history descriptive appendix without tuning against it.

The timing narrative will be checked, not assumed. Tokyo cash equities open
at 09:00 Japan time, corresponding to 20:00 EST or 21:00 EDT. Hong Kong cash
continuous trading begins at 09:30 Hong Kong time, corresponding to 20:30 EST
or 21:30 EDT; its pre-opening session begins at 09:00 local time. These are
clock conversions from the published local schedules, not evidence of their
effect on NQ. Keep the user's fixed NY window and report EST/EDT separately.
Actual exchange-open attribution would additionally require historical local
holiday calendars; until then, label these as scheduled clock markers.

Measure NQ volume, range, and absolute returns in 15-minute bins from 18:00
to midnight, including the 18:00–20:00 context. Show seasonal regimes and
yearly counts. Do not impose a high-volume filter because of the narrative.

Sources: [JPX trading hours](https://www.jpx.co.jp/equities/trading/domestic/01.html),
[HKEX trading hours](https://www.hkex.com.hk/Services/Trading-hours-and-Severe-Weather-Arrangements/Trading-Hours/Securities-Market?sc_lang=en).

## 3. Inputs, prices, and data quality

Pin the existing `volume_lead_unadjusted_v1` publication, its NQ partitions,
roll schedule, and calendar context. The final back-adjusted publication is
also pinned for comparison and lineage. All 17 annual NQ partitions in each
variant exist. The planning lock records manifest hashes, not a completed
full partition verification. Resolve roots using workspace path configuration.

For price-anchored VP reconstruction, use the selected contract's actual
unadjusted coordinates as the primary frame. This differs from the general
preference for adjusted indicators: absolute row-grid phase matters here,
and mixing raw contract prices across rolls can create artificial nodes.
Exclude events whose active profile/reference lookbacks span different raw
contracts, and require full warm-up after a roll. Define affected feature
availability explicitly rather than quietly shortening the HVN history or
dropping a reference filter. Report the lost sessions. Construct the source
indicator state literally, but exclude contaminated events from primary results.

If comparison with an adjusted TradingView continuous chart is desired, use
a separately labeled adjusted-snapshot sensitivity. It is not point-in-time
certified. Compare row-grid phase and roll effects, not just a constant price
offset. Never use synthetic adjusted values directly for fills or P&L. Align
source bars by timestamp, contract identity, and adjustment, never by row order.

Primary data checks:

- Timestamp order, duplicates, OHLC consistency, price encoding, tick alignment,
  contract/roll identity, volume validity, source condition flags, and hashes.
- Expected schedule within each consumed window, respecting known scheduled
  closures. The old afternoon equity pause does not automatically invalidate
  an otherwise complete 18:00–00:00 one-minute sample before 2021.
- Full 18:00-to-signal overnight history; valid warm-up for active weekly,
  prior RTH, PDH/PDL, and composite HVN references; complete future minute paths
  for each reported horizon. Audit these separately by setup and feature need.
- No forward-filling missing bars. An absent minute may represent no trading,
  a schedule exception, or a data issue; absence alone is not proof of corruption.
- Primary strict profile/path completeness, with a separately labeled
  available-bar sensitivity if strict exclusions are substantial. Never equate
  30 available bars with 30 elapsed minutes across a gap.
- Holiday/early-close, roll, warm-up, gap, late-entry, and degraded-source flags
  receive separate counts and denominators. Do not inherit the existing VWAP
  release's whole-day eligibility without evaluating this study's windows.

Future path completeness and any full-day eligibility are retrospective sample
decisions. Preserve all candidate events, including later-excluded ones, and
show exclusions. These flags must never become live signal features.

## 4. Indicator reproduction and causal snapshots

The byte-preserved supplied script is in
[reference/vp_hvn_levels_dev.pine](reference/vp_hvn_levels_dev.pine).
Its defaults form the baseline, not a searched set of parameters:

| Component | Baseline |
|---|---|
| Main VP | 16 ticks per row = 4 NQ points; 70% value area |
| Futures / RTH / overnight | 18:00–17:00 / 09:30–16:00 / 18:00–09:30 NY |
| Composite HVN history | 10 completed futures sessions plus developing session |
| HVN row / smoothing | 4 ticks = 1 point; centered 3-row average |
| Peak height / neighborhood | At least 20% of smoothed maximum; ±5 rows |
| Prominence / width | At least 10% of peak; expand 60% toward prominence base |
| Band width cap | 8 ticks = 2 points |
| Node suppression / VP clearance / zone clearance | 8 ticks each |
| Candidate rebuild | 15 elapsed minutes at completed chart-bar closes |
| Selected zones | At most 2 above and 2 below price |
| Active reference filters | All reference-level groups enabled, as supplied |

Main VP divides each bar's volume equally among touched fixed price bins.
POC is the lower price coordinate of the first maximum bin, with lower-price
ties winning. Value area expands one bin at a time from POC; equal adjacent
volumes favor the upper side. VAH/VAL are the reported bin coordinates, not
substituted conventional outer edges. Missing volume is treated as zero.

HVN uses a grid anchored at the composite low, smoothed row volumes, local
peaks with lower-price tie preference, and prominence against the higher of
the two side-trough minima. Zone strength is peak height, not total band volume.
Retain the source's row cap, adaptive step, capacity behavior, and exact gap
inequalities. Smoothing with an even requested width actually spans the next
odd number of interior rows; baseline three avoids that ambiguity.

Reproduce weekly reset using the documented NQ TradingView weekly boundary;
verify it explicitly rather than assuming a New York calendar Monday. PDH/PDL
are full futures-session extremes. The displayed previous-RTH references switch
to the newly completed RTH profile after RTH ends. Developing RTH is hidden
after the new 18:00 futures session, so it normally contributes no Asia filter.
All actually enabled, available reference levels affect HVN clearance.

At the start of minute t, save a snapshot calculated only from completed bars
through t−1. Detect touches/crossings during t against this **fixed known
snapshot**, confirm any close condition after t completes, and hypothetically
enter at the next contiguous one-minute open. Update the profile with minute t
for the next snapshot. Record both pre-bar and post-bar values. This distinguishes
price movement from a level moving across a stationary price.

This primary historical model is a one-minute approximation of the live
indicator. It cannot reconstruct tick-by-tick developing profiles or transient
live HVN selections from OHLCV. A secondary close-snapshot variant may use
the signal candle in its profile, explicitly labeled and kept separate.

For HVNs, reconstruct history at every scheduled rebuild, not only at the final
historical chart bar. Seed at the first complete futures-minute close, then
rebuild when at least 15 elapsed minutes have passed, and on a new futures
session. This is a declared historical adaptation of the source's last-bar
execution gate. Keep candidates cached between rebuilds. Select using the
pre-bar price and known reference levels: remove price-containing/reference-
colliding zones, suppress weaker eligible neighbors, sort survivors by distance
to their midpoints, then select with zone clearance and side quotas. A weaker
neighbor may return when the stronger one becomes ineligible.

The supplied boxes extend back to session start and are deleted/recreated on
the last bar. Their drawn left edge is not an availability timestamp. Give
each candidate a rebuild identity, bounds, peak, strength, available-at time,
selection rank, filter decisions, and last observed status. Match nodes across
rebuilds by overlapping bands and nearby centers deterministically; retain
split/merge ambiguity instead of pretending rank R1/S1 is a permanent node ID.

Reusable causal VP/HVN features belong to Bhishma. Before implementation,
prepare a dataset request for a new, versioned NQ one-minute profile/snapshot
release. Study-specific event state machines and excursions stay in this study.
No existing release will be rebuilt. The source alone is pinned now; the new
feature release and its manifest must be pinned before a study execution.

## 5. Exact frozen setups

Common baseline: 1 tick beyond a boundary to establish a breakout, a 1-tick
touch tolerance, maximum 60 minutes between breakout and trigger, and no
same-candle breakout-and-retest inference. Every pending setup is canceled at
midnight or a futures-session change. Opposite breakouts cancel the old arm and
may create a new one. Track boundary migration and price-versus-level crossing.

### A. Overnight POC return fade — confirmed primary interpretation

Upper case: a completed bar closes at least 1 tick above its known overnight
VAH after the preceding close was not outside that same boundary. Arm an upper
excursion. On a later bar, price returns from above and its range intersects
the known developing POC ±1 tick. **Proposed trade: long at the next open**, to
fade the downward return toward POC. The lower excursion is mirrored: below
VAL, return upward to POC, then short. Require the preceding close to be on
the approach side of the POC used for touch detection. No touching event can
be inferred solely from POC migration.

Allow origins during 18:00–20:00 with the same 60-minute expiry. First valid
POC return consumes that excursion. A repeat requires a fresh breakout; a bar
remaining outside does not keep rearming. Retain unreturned and expired
excursions for the opportunity funnel. A secondary rejection-confirmed entry
requires a touch and close back on the long/short side of POC before next-open
entry. Do not make confirmation a prerequisite for the baseline touch setup.

Record the breakout's VAH/VAL/POC and the touch-time developing values. Primary
uses developing POC; frozen breakout-time POC is a named sensitivity. Contextual
target references are touch-time VAH for a long and VAL for a short, frozen
before entry, with their movement and reachability disclosed.

**Excluded alternative:** upper excursion, close back inside VAH, then short
toward POC; lower excursion, close back inside VAL, then long toward POC.
That opposite-direction POC-target hypothesis is not part of protocol 1.0.0.

### B. Value-area breakout, retest, and continuation

Upper case: establish a VAH breakout as above. On a later bar, price approaches
the known developing VAH from above, its range intersects VAH ±1 tick, and it
closes at or above VAH. Enter **long next open**. Lower case: break VAL,
retest from below, close at or below VAL, and **short next open**.

Require the preceding close to be on the breakout side of the boundary used
for the retest. A retest encounter that closes more than 1 tick back inside
value cancels that arm. A close within tolerance but failing confirmation is
retained as unconfirmed; no entry is inferred. One accepted retest consumes
the breakout. Gap-across-level bars without a genuine range intersection are
not touches. Record all breakout, cancellation, expiry, and no-retest counts.

Primary retest follows the developing boundary known before the retest candle.
Frozen breakout-time VAH/VAL is a separately labeled sensitivity. A touch-only
variant omits the retest-close confirmation; it still enters next open.

### C. Selected composite HVN fade

An HVN must be displayed in the snapshot before the signal minute begins.
For an overhead selected zone approached from below, the later candle's range
intersects that saved band: **short next open**. For a selected zone below
price approached from above: **long next open**. Require preceding close
outside the zone on the approach side. No entry when a zone first appears
already containing price; no hypothetical fill at the exact band edge.

Use saved pre-touch bounds even if the live selection would remove the node
once price enters it. Record whether it remains eligible in the post-bar
snapshot. Primary is first touch per matched node per futures session, without
restricting touch to only R1/S1. Report near/far rank separately. If two bands
are touched in one candle, preserve the ambiguity; exclude that event from the
primary unique-node cohort and retain a sensitivity using the pre-bar nearest
rank. Never assume intraminute order.

Rejection-confirmed sensitivity: overhead touch and close below the near band
edge before short entry; lower touch and close above the near edge before long
entry. Secondary repeat touches require departure by 8 ticks beyond the band
and at least a 15-minute lockout; ambiguous node matches cannot create a fresh
first-touch event. Preserve every filtered-out candidate and reason.

## 6. Event counting, entry, and overlap

Each setup is a state machine with a retained funnel: candidates → armed →
triggered → next-open entry → valid horizon. Store rejected, suppressed,
expired, unavailable, censored, and invalid-path records with explicit reasons.

Primary descriptive cohort uses the first valid trigger per excursion for A/B
and per selected node/session for C, with a **15-minute setup-and-direction
lockout** after an accepted signal. Suppressed signals do not restart it. Retain
unsuppressed candidates; sensitivities use lockouts of 0 and 30 minutes.

The next minute must exist and its open must be within 20:00–00:00. Measure
from its actual unadjusted open, even if it gaps away from the reference. Retain
entry distance and show a prespecified near-entry subset within 2 points of
POC/VA boundary, or within 2 points of the HVN band. Do not cherry-pick a new
distance cutoff after outcomes. For stop/target scenarios, define position
overlap separately; the excursion study can contain overlapping hypothetical
paths and cannot be read as portfolio returns.

Signals shared by multiple setups receive multi-setup flags and a joint count.
Do not sum their apparent opportunities or combine independently calculated
P&L as though simultaneous capital were unconstrained.

## 7. MAE, MFE, and path measurements

For entry E and subsequent unadjusted bars through horizon H:

- Long MFE = max(0, maximum high − E); long MAE = max(0, E − minimum low).
- Short MFE = max(0, E − minimum low); short MAE = max(0, maximum high − E).
- Terminal signed move = direction × (last close − E), direction +1/−1.
- Include the complete entry candle; exclude the signal candle and all
  pre-entry prices. A 30-minute path entered at 20:05 uses bars opening
  20:05 through 20:34, ending at 20:35.

Report NQ points, ticks, and dollar equivalents for one NQ contract. NQ is
$20/point, 0.25 points/tick, hence $5/tick per
[CME specifications](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html?videoId=6391019386112).
Dollar excursions are path magnitudes, not realized profits/losses.

Also normalize by the mean one-minute true range over the prior 60 complete
minutes, known before the signal candle, and by signal-time value-area width
where nonzero. Retain null normalized results and denominator counts when
warm-up or width is undefined; never silently replace a zero denominator.

For each setup/side/horizon/split, provide event count, distinct sessions and
weeks, mean, median, p25/p75/p90/p95, terminal-positive share, and approximate
95% uncertainty intervals. Add:

- Joint MAE/MFE distributions and median signed path, with time to first
  favorable/adverse thresholds and first occurrence of maximum excursions.
- Target-before-adverse-threshold probabilities. Primary illustrative race:
  +1 versus −1 prior-60-minute true-range unit within 30 minutes. Secondary
  fixed NQ distances 2, 4, 8, 12, and 20 points, explicitly descriptive.
- MAE before first reaching each favorable threshold; show how many never
  reached it. Winner-conditioned pre-target MAE cannot stand in for the
  unconditional stop requirement.
- Structural reference hits using entry-frozen known levels (POC/value edges
  as applicable), with moving-reference results separately labeled. Do not
  remove entries where a supposed target is already behind the entry price.
- Same-bar favorable/adverse races are ambiguous. Show favorable-first and
  adverse-first bounds, ambiguous share, and neither-hit/time-expiry share.
  Independent MAE/MFE values require no invented ordering.

Optional prespecified stop/target illustrations use first passage, next-open
entry, adverse gap handling at the observed open, and a midnight/time expiry.
Show target/stop/time-exit counts and conservative ambiguity bounds. Add
round-trip cost sensitivities of 0, 1, 2, and 4 ticks plus a separately stated
commission assumption if a net figure is presented. OHLCV has no bid/ask,
queue position, or tick ordering; favorable fills cannot be certified.
No optimized stop/target, expectancy, Sharpe ratio, or strategy recommendation
will be inferred merely by pairing each event's maximum MFE with maximum MAE.

## 8. Comparisons and statistical discipline

Primary comparison family is the three setup definitions, with long/short
reported explicitly, at 30 minutes under baseline settings. Other horizons,
entry variants, and context slices are secondary. Retain all variants, including negative and
inconclusive results; no sweep over indicator parameters in the first run.

Compare with matched eligible Asia-session minute entries in the same side,
year, hour, and pre-signal volatility quintile, using development-defined
quintile boundaries and a fixed random seed. Match only on causal context,
not later outcomes, and show balance/support. Equalize session weights as a
sensitivity. This asks whether an excursion advantage exceeds ordinary NQ
movement at comparable times; it does not establish causation.

Report 20:00–21:00, 21:00–22:00, 22:00–23:00, and 23:00–00:00; EST/EDT;
year and split; side; first/repeat event; pre-20:00 origin; prior-60-minute
volatility; 18:00–20:00 volume/range; overnight profile width/drift; breakout
distance/duration; and HVN rank, strength, age, and clearance. Use development
data for any quantile cutoffs. Do not create a large interaction search or
claim a best cell from sparse subgroups.

For dependence, primary uncertainty uses moving blocks of two consecutive
ISO weeks (2,000 replicates, seed 1414); four-week blocks are a sensitivity.
Resample whole blocks, carrying all events and their controls together. This
addresses overlapping paths and shared HVN history more honestly than treating
every candle as independent. Show counts of sessions/weeks and leave-one-year-
out stability. Tiny cells remain visible but are labeled low support; proposed
minimum for substantive subgroup interpretation is 50 events, 30 sessions,
and 12 weeks. Thresholds are reporting safeguards, not filters on individual
signals.

Use effect sizes and intervals. If formal p-values are added, predeclare
metrics and adjust across the primary family; secondary slices stay exploratory.
Validation and final-check rules stay fixed even when development is disappointing.

## 9. Deliverables

1. Data-quality and opportunity funnel by year, setup, side, and exclusion.
2. Saved one-minute profile/rebuild/selection snapshots with causal timing.
3. Candidate and accepted-event ledgers, level identities, entry references,
   context, censoring, horizon flags, and hashes/retention locators.
4. MAE/MFE tables, distributions, signed paths, threshold-race tables with
   ambiguity bounds, matched-baseline differences, and robustness comparisons.
5. Year-by-year and chronological-split report, with 2026 explicitly YTD.
6. Representative charts chosen by a fixed rule, covering success, failure,
   ambiguous events, and exclusions, with profile evolution visible. Do not
   illustrate only attractive trades.
7. Offline HTML and Markdown reports generated from saved numbers. Each setup
   receives a conclusion: supported descriptively, inconclusive, or adverse
   evidence, with specific metrics and practical limits.
8. Frozen settings, source script, feature/data locks, exact commands, source
   revision/dirty snapshot, environment lock, numerical checks, and artifact
   hashes. Stage under `work/`; seal a new unique run only after verification.

No web publication or deployment is included. No current strategy card will
present the hypotheses as tested findings.

## 10. Execution sequence and gates

**Gate passed:** implementation is authorized and setup A's entry and direction
were clarified before the protocol freeze. The feature release is pinned.

**Execution:** use the pinned Bhishma causal features and implement local
event/outcome logic. Validate known synthetic examples and small feature-only
sessions before examining full outcomes. Required examples include VP mass conservation,
bin/tie/value-area rules, sessions/DST/week boundaries, roll contamination,
HVN prominence/width/filter/selection order, node disappearance at touch,
cache cadence, moving-level false crossings, same-bar multi-node ambiguity,
all mirrored setups, lockout, next-open entry, gaps, midnight, and threshold
race ambiguity. Document Pine parity comparisons and any deviations.

**Full run:** validate the complete declared
primary family and secondary variants, compute development then unchanged
validation/final-check results, and produce all saved evidence. Full partition
hash checks and cross-checking adjusted/unadjusted lineage precede execution.
Use focused numerical tests and the study's audits; run workspace checks only
when package/configuration/feature work requires them.

**Delivery:** interpret the verified report, retain failed hypotheses and
exclusions, and seal an immutable run. Decide any next strategy, ES/GC extension,
or deeper execution research from that evidence in a separate step.

Planning verification used the documentation checker and research-index
freshness check. These do not verify numerical logic or source-data
integrity; no completed evidence exists yet.
