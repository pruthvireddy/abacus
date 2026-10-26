# Potential VWAP strategies and the statistics to investigate

Prepared September 22, 2026. Status: **research proposal only**. No strategy study, outcome computation, or backtest has been run. The checks performed for this proposal were limited to documentation, manifest hashes, published coverage, Parquet schemas, and a small sample of feature rows.

The aim is to identify where VWAP behavior might provide useful predictive information: how often a setup occurs, how much favorable movement follows, how much adverse movement comes first, and whether the behavior survives comparison with an appropriate baseline. These are six candidate families, with proposed definitions to make them testable. All numeric thresholds below are starting conventions, not parameters selected from results.

## The six candidates

| ID | Candidate | Question it answers | Most useful initial statistic |
|---|---|---|---|
| 1 | Fade the first close outside 2σ | Does an extreme close lead to a useful retracement? | Probability of a favorable move before an equally sized adverse move, plus full VWAP return probability |
| 2 | Fade after price closes back inside 2σ | Does waiting for re-entry improve the remaining opportunity? | Improvement after confirmation, alongside the opportunities lost while waiting |
| 3 | Return to VWAP after a meaningful departure | In how many sessions does price return, and how long does it take? | Return rate among sessions with a departure, by elapsed time and session end |
| 4 | Bounce on the first VWAP retest | When price comes back to VWAP, does it resume its original direction? | Bounce target reached before an equally sized adverse price move, with VWAP penetration reported alongside |
| 5 | VWAP cross, acceptance, and retest | Does VWAP act as support or resistance after price changes sides? | Continuation after a held retest, compared with entering at the original cross |
| 6 | Continue with a sustained move outside 2σ | When does an extreme persist instead of mean reverting? | Continuation versus fade outcomes from the same confirmation time |

Suggested research order: **3 first, then 1 and 2 together, then 4, then 5 and 6**. Candidate 3 establishes the return behavior that the other ideas depend on. Candidates 1 and 2 directly investigate the first hypothesis raised by the user; candidate 4 directly investigates the bounce hypothesis. This is an order for learning, not a ranking of expected profitability.

## What the inspected data supports

The pinned release is `session_anchored_vwap__1.0.0`, with datasets `session_anchored_vwap_2m_v1` and `session_anchored_vwap_5m_v1`. Its 115-column schema and sampled Parquet files contain OHLCV, contract identity, availability timestamps, session flags, and four complete anchor groups. Each group includes VWAP, sigma, 1σ/2σ/3σ bands, distances, anchor age, cumulative volume, and completed-bar cross/exit/re-entry events.

| Product | Published eligible session dates | Eligible days | 2m rows | 5m rows |
|---|---|---:|---:|---:|
| ES | 2021-06-28–2026-09-18 | 1,037 | 715,530 | 286,212 |
| NQ | 2021-06-28–2026-09-18 | 1,177 | 812,130 | 324,852 |
| GC | 2016-02-11–2026-09-18 | 825 | 569,250 | 227,700 |

These are published coverage counts, not counts of strategy opportunities. Coverage is discontinuous and product-specific. For example, GC has only 35 eligible days in 2023 and 62 in 2024. Keep each product's eligible population; a missing GC day does not remove an ES or NQ day. Use a common calendar range only for a specifically labeled cross-product comparison.

All times below are America/New_York, with daylight saving handled through that timezone.

| Anchor | Starts | Published membership window | Accumulation ends |
|---|---|---|---|
| Globex | 18:00 on the preceding date | Full trading session, 18:00–17:00 | 17:00 |
| Asia | 20:00 on the preceding date | 20:00–03:00 | 17:00 |
| London | 03:00 | 03:00–09:00 | 17:00 |
| NY | 09:30 | 09:30–16:00 | 17:00 |

For the main comparisons, study Globex VWAP throughout the trading session, and each local anchor within its own membership window. Within Asia, London, and NY, also compare the local anchor with Globex over the same observation window. A secondary view can follow older anchors until 17:00. The gaps 18:00–20:00, 09:00–09:30, and 16:00–17:00 have no local membership flag; label them explicitly and use Globex for the primary view.

Two-minute and five-minute VWAPs are calculated independently from their respective bars. Compare them over the same elapsed-time horizons; they are correlated views of the same market history.

Use **ticks and points** for ES, NQ, and GC. Sampled `min_tick` values convert to 0.25 points for ES/NQ and 0.10 for GC; future analysis must read the row's metadata. An equal tick count does not imply equal dollar value or equal difficulty across products.

## Shared definitions that make the statistics meaningful

**A mature anchor.** Start the primary studies after 30 minutes of anchor accumulation, with a valid VWAP and positive sigma. At inception, sigma is zero; sampled first NY bars confirm this. Treat the first 30 minutes as a separate optional study. Check 20- and 40-minute warm-ups later as limited sensitivity tests.

**Distance.** Let `z = (close − VWAP) / sigma`, using the completed signal bar. Positive values are above VWAP. The published `*_distance_sigma` already contains this dimensionless ratio. Some schema text incorrectly labels this field and some boolean events with price units; the Arrow types, indicator contract, and calculation establish their meaning. This proposal does not alter the publication.

**What 2σ means.** Sigma is the volume-weighted dispersion of completed output-bar HLC3 around the accumulated VWAP. A close outside 2σ is an empirical setup to investigate; the formula supplies no 95% containment or mean-reversion probability.

**An excursion.** For candidates 1, 2, and 6, begin an episode at the first valid published exit beyond ±2σ after warm-up. Outside means strictly beyond the band. Repeated outside closes belong to that episode. Rearm after a completed close is back within ±1σ, including equality. Keep the original episode ID when studying re-entry or persistence. Episodes already outside at the warm-up boundary are labeled separately from fresh exits.

**Two meanings of returning to VWAP.** Report both:

- **Return to the original level:** freeze VWAP at departure and ask whether later price reaches that level. This measures the price travel needed to retrace the original distance.
- **Contact with the evolving VWAP:** for each future output bar, use only the latest VWAP available before that bar begins, held fixed through the bar. This measures interaction with a reference that updates as new bars complete.

VWAP can move toward price. A high rate of contact with the evolving VWAP may therefore coexist with modest price retracement. Report actual favorable movement alongside both return rates. Updating a target also differs from leaving a resting target at its original price.

**Touch.** The primary contact zone is the known VWAP ±1 tick. A subsequent bar touches when its range intersects that zone. Equality at its boundary counts. The VWAP must have been available before the tested bar; comparing a bar's high/low with its own final VWAP would use a level that was unknown during that bar. A gap completely through the zone is a separate side-change event, not proof of a touch. A close crossing contemporaneous VWAP is also a distinct, valid completed-bar event.

**Timing.** Signals become available at `available_at`, which equals the bar's exclusive close. The primary price reference for subsequent movement is the next available unadjusted bar open. This is an idealized entry convention; execution research would add explicit latency and costs. For a touch identified from a completed 2m/5m bar, begin bounce outcomes after that bar. Its favorable extreme might have occurred before the touch and cannot count as post-touch profit.

**Outcome horizons.** Use 30 elapsed minutes as the primary short-horizon comparison; 10 and 60 minutes are secondary. Analyze return by the named window's end separately. For a complete fixed horizon, require signal-time capacity for the entry and entire horizon before that window ends. Report excluded late events. For return by window end, a non-return is a non-return by that deadline; retain it in the denominator. Reset all episodes at the trading-session boundary.

**Comparable movement thresholds.** The initial common test is a favorable move of `0.5 × signal sigma` before an adverse move of the same size, measured from the entry reference within 30 minutes. Freeze sigma at signal time and round the distance upward to an integer number of ticks. Report the resulting distances in ticks. This is a research comparison, not a chosen stop/target for live trading. Also show favorable/adverse movement distributions and probabilities for illustrative 4/8/16/32-tick moves. Inspect cost feasibility before interpreting the smallest moves economically. A later 0.25σ/1σ sensitivity is a short declared grid, not a search for the best cell.

## 1. Fade the first close outside 2σ

**Hypothesis:** after a mature anchor's first extreme close, enough price retracement follows to create a useful opportunity before further adverse extension.

Use `*_exit_above_upper_2sigma` for a potential short fade and `*_exit_below_lower_2sigma` for a potential long fade. The signal is the completed exit bar, and the direction is toward VWAP. Use one initial signal per excursion. Keep upper and lower exits separate as well as combined.

Proposed statistics:

- Episodes per 100 eligible sessions, percentage of sessions with an episode, and the distribution of initial distance in ticks and sigma.
- **Primary:** probability of the favorable 0.5σ barrier preceding the adverse 0.5σ barrier within 30 minutes.
- Probability and time to a partial retracement, original VWAP, and evolving VWAP; report 10/30/60-minute and window-end views.
- Signed forward movement, maximum favorable excursion (MFE), and maximum adverse excursion (MAE), including adverse movement before a successful return.
- Frequency and size of further extension, including reaching the signal-time 3σ level before retracing. Keep the level frozen for this specific statistic; if it has already been passed at signal or entry, label it already passed and report that share separately from later hits.

Compare with time- and volatility-matched lesser departures, such as fresh 1–2σ excursions. Initial distance changes the difficulty of reaching VWAP, so a raw full-return-rate comparison is insufficient; compare equal movement barriers and adjust or stratify by starting distance where there is overlap.

**What would be useful:** repeatable favorable movement with manageable adverse tails, adequate frequency, and improvement over comparable departures. “Usually returns eventually” is insufficient if severe extension commonly precedes the return.

## 2. Fade after price closes back inside 2σ

**Hypothesis:** the first completed re-entry offers stronger evidence of rejection than the original outside close, while retaining enough movement toward VWAP.

Link the first `*_reenter_from_above_2sigma` or `*_reenter_from_below_2sigma` to candidate 1's excursion. Equality with the relevant band counts as re-entry. Signal at the re-entry bar close, then use the next unadjusted bar open. If price has already crossed the relevant VWAP or the entry is already beyond the intended mean-reversion target, record that the opportunity was consumed; do not label it a fresh favorable target ahead of the entry.

Proposed statistics:

- Fraction of all outside episodes that re-enter; time spent outside; fraction with no confirmation before the window ends.
- Movement captured or missed while waiting, additional adverse extension avoided, and remaining distance to VWAP at confirmation.
- **Primary:** the same 30-minute symmetric-barrier probability after re-entry as in candidate 1, plus forward movement and MFE/MAE.
- Return to VWAP after re-entry and the fraction of confirmations leaving too little distance to justify costs.

Report conditional outcomes after confirmation and a paired policy comparison over **all original outside episodes**. In that policy comparison, a never-confirmed episode is no trade for the waiting policy, with zero trading P&L; it remains in opportunity counts. Use a shared deadline of the earlier of 60 minutes after the initial exit or window end. The standalone 30-minute post-entry statistics answer a different question and must carry their own denominators.

**What would be useful:** confirmation reduces adverse exposure enough to compensate for later entry and missed opportunities. A higher win rate on a selected subset alone would not establish that improvement.

## 3. Return to VWAP after a meaningful departure

**Hypothesis:** after price establishes meaningful separation from a mature VWAP, a subsequent return is sufficiently frequent and timely to inform trade targets or a reversion entry rule.

For each product, timeframe, anchor, and observation window, identify the first completed close at least 1σ and at least 4 ticks from VWAP after both window start and anchor warm-up. Equality qualifies. Label cases already far away at the start of eligible observation separately from a fresh departure observed afterward. The primary unit is one departure per window, rather than every away bar. Later independent departure/return cycles are secondary.

Proposed statistics:

- **Denominators:** eligible windows; windows with a mature anchor; windows with a qualifying departure; windows with a return. Show both return/departure and departure/all-window rates. Keep no-departure windows visible.
- **Primary:** probability of returning to the frozen departure-time VWAP by the observation window's end, conditional on departure. Show evolving-VWAP contact alongside it.
- Return probability within 10/30/60 minutes, with the number of observations supporting each horizon; time-to-return distribution with non-returners retained in the analysis.
- Maximum extension before return, favorable price movement actually achieved, and distance remaining at window end when no return occurs.
- Number of completed departure/return cycles per window; percentages with zero, one, two, or more. Require a new qualifying departure after each return to avoid counting adjacent touching bars repeatedly.
- Return probability conditional on not having returned at all since the original departure after 10, 30, or 60 minutes, with distance and all conditioning measured at that elapsed-time landmark. Returning and then departing again begins a different episode.

**Potential strategy use:** this supplies the basic “VWAP magnet” map and possible timeouts. A tradeable variant would enter toward VWAP after a prescribed departure and would need an explicit adverse exit. A session-level return percentage by itself is a behavioral statistic.

## 4. Bounce on the first VWAP retest

**Hypothesis:** the first return from an established side often leads to a move back toward that side before meaningful penetration or loss.

Before the retest bar begins, require price to have closed on the same side of contemporaneous VWAP for the preceding 10 elapsed minutes, with at least one completed close at least 1σ and 4 ticks away during the current departure. Track the first causal touch of the known VWAP zone after those conditions are satisfied. Long direction follows an approach from above; short direction follows an approach from below. One touch setup per departure is primary.

Proposed statistics:

- **Primary:** among all qualifying first touches, the probability of moving 0.5 frozen signal sigma in the bounce direction before the equal adverse move within 30 minutes, starting at the next bar open.
- Bounce-size distribution in ticks: favorable movement, adverse penetration, time to favorable thresholds, and signed movement at 10/30/60 minutes.
- Frequency of a close back on the approach side after the touch versus a close through VWAP; a close exactly at the zone boundary is neutral for confirmation.
- First retest versus second and later retests, with a meaningful new departure required between retests.
- A confirmation variant that waits for the touch bar to close beyond the zone on the original side, with outcomes starting at the following open.

The all-touch population answers “how often does a touch bounce?” The confirmation subset answers “what follows once a rejection is visible?” Publish both denominators. A bounce that occurs entirely inside the touch bar is descriptive and is not credited as attainable post-signal movement.

**What would be useful:** favorable movement persists after the touch is observable, with limited penetration. Compare first retests with matched later retests and near-VWAP approaches that do not reach the contact zone; disclose that these are observational comparisons.

## 5. VWAP cross, acceptance, and retest

**Hypothesis:** after price crosses VWAP and establishes itself on the new side, a held retest predicts further movement in that direction.

Begin with a published completed-bar VWAP cross. Within the next 10 minutes, require a completed close on the new side by at least `max(2 ticks, 0.25 × current sigma)`; the crossing bar itself may satisfy acceptance. After acceptance, look for the first causal VWAP-zone retest within 30 minutes. It confirms only if that retest bar closes beyond the known zone on the new side. Enter the new-side direction at the following open. An accepted opposite cross cancels the setup; a timeout produces no confirmed trade.

Proposed statistics:

- Counts and conversion rates through cross → acceptance → retest → held retest. Report failure and timeout at each step.
- **Primary:** 30-minute symmetric-barrier probability following a held retest; signed movement, MFE/MAE, and time to favorable thresholds.
- Probability of reaching the acceptance-time 1σ/2σ level in the new direction where that frozen level remains ahead of entry; otherwise mark the target already passed.
- Whipsaw probability: a completed cross back to the old side within 10/30 minutes.
- Comparison with entering at the original cross, including crosses that never produce a held retest. Use all original crosses as the paired policy population and a shared deadline of the earlier of 60 minutes after the cross or window end; an unconfirmed setup is no trade for the retest policy.

**What would be useful:** waiting for acceptance and a retest improves the tradeoff between opportunity frequency and adverse movement. Candidate 4 begins with an established side; this candidate begins with a change of side. Some events can overlap, so retain shared event identifiers and do not count them as independent evidence.

## 6. Continue with a sustained move outside 2σ

**Hypothesis:** some extreme excursions represent persistent directional movement, and a known period of sustained outside closes identifies continuation better than fading.

Starting at candidate 1's first outside close, require every subsequent completed close through 10 minutes later to remain beyond the same 2σ band: five further 2m closes or two further 5m closes, in addition to the initial exit close. Evaluate each close against its own contemporaneous band. Equality breaks the outside run. This measures persistence of observed closes, not uninterrupted intrabar trading outside the band. Signal at that 10-minute confirmation close and enter in the outward direction at the next open. Use one signal per excursion. No eventual “trend day” label is allowed in the signal.

Proposed statistics:

- Fraction of initial outside episodes that persist for the required duration, and movement already completed before confirmation.
- **Primary:** continuation versus fade symmetric-barrier outcomes from the identical confirmation time and entry reference. These are paired mirror outcomes with shared counts, not two independent pieces of evidence. Count ambiguous ordering and timeouts identically for both directions.
- Further extension, signed forward movement, MFE/MAE, and the probability and timing of re-entry and full VWAP return.
- Breakdown by the VWAP slope and anchor agreement observable at confirmation.

A comparison with episodes that failed to persist must start at a common elapsed-time landmark, with comparable follow-up. Do not use eventual persistence to retroactively filter the immediate fade in candidate 1.

**What would be useful:** a condition observable in real time that helps distinguish continuation from reversion. This also tests a direct competing explanation for outside-band events.

## Statistics that would help identify an edge

Each candidate's scorecard should contain the following, separately by product and direction:

| Statistic | What it tells us |
|---|---|
| Events and distinct sessions; opportunities per 100 sessions | Whether a seemingly strong result has enough independent occurrences and practical frequency |
| Primary probability with 95% uncertainty interval | How often the predefined behavior occurs and how precisely it is estimated |
| Target first / adverse barrier first / neither / ambiguous | The full outcome distribution; hitting a small target eventually can hide large prior losses |
| Mean, median, 10th/90th percentiles of signed movement | Directional tendency, typical outcome, and tails |
| MFE, MAE, and adverse movement before success | Whether the favorable path is tolerable and potentially capturable |
| Time to target, VWAP return, and failure | Useful holding periods and the cost of waiting |
| Difference from a matched baseline, with an interval | Whether the setup adds information beyond ordinary time, volatility, and distance effects |
| Results by year, session window, and timeframe | Whether an effect is stable or concentrated in one slice |
| Later: mean net trade, profit factor, drawdown, and break-even costs | Whether observed behavior can survive explicit execution assumptions |

Baseline matches should use product, anchor, timeframe, time of day, anchor age, pre-event volatility, and starting distance where appropriate and supported by overlapping samples. Define matching bins from development data only, report unmatched events, and avoid conditioning away the feature being tested. There is no universal 50% benchmark for unequal or moving targets. Session-end return rates should be compared at similar departure times and distances.

Useful secondary conditions, introduced one at a time:

- **VWAP slope:** movement of that anchor's VWAP over the preceding 10 minutes, normalized by current sigma; use only mature observations with the needed history.
- **Globex/local agreement:** price on the same side of both available mature anchors versus opposite sides.
- **Nearby VWAPs:** a proposed confluence zone when Globex and the current local VWAP are separated by at most 0.25 times the smaller positive sigma. Compare confluence retests with otherwise similar isolated retests; do not count an anchor pair as two independent setups.
- **First versus later excursion/retest** and **time of day**. Use a small number of broad groups before finer segmentation.

## Execution, uncertainty, and sample rules

**Price source.** All actual fill and P&L research must use `volume_lead_unadjusted_v1`. Join by product, session date, raw symbol, instrument ID, and interval; reconcile 1m bars to the exact output boundaries. To express a feature level in the contract's price coordinates, subtract the session's `price_adjustment × 1e-9` from the adjusted level, then apply explicit order-price tick rounding. Validate that translation against unadjusted OHLC. Fills still come from unadjusted prices and an execution model, not from adjusted feature values. Positions end within the study window and never bridge a roll in the primary design.

**Path ambiguity.** Use the unadjusted 1m series to order post-signal target/stop events where possible, while updating VWAP only when its selected 2m/5m feature becomes available. One-minute OHLC may still contain both barriers. Retain those cases, report their count, and give pessimistic/optimistic bounds; do not assume favorable ordering or silently remove them. Range contact is not proof of a limit-order fill, and gaps require an explicit fill convention.

**Levels passed before entry.** For every level-based target, record whether the next entry reference has already reached or crossed it. Such movement may belong in the descriptive post-signal path, but is not a profitable target hit after entry. Report these cases explicitly and keep a consistent no-trade convention in the paired policy comparisons.

**Costs.** Price-path statistics can be specified now. Commission, spread/slippage, order type, latency, position size, and contract dollar multipliers must be fixed before reporting profitability. A later cost sensitivity should include a stated base case and worse fills. A high hit rate is useful only in relation to the size and timing of losses and costs.

**Sample construction.** Report eligible product-days → mature anchor windows → qualifying episodes → evaluable outcomes, with each exclusion reason. Keep undefined event flags separate from evaluated false flags. Eligibility is known retrospectively at the whole-day level; all findings are conditional on retrospectively complete product-days. It cannot be used as an entry-time filter. Show exclusion rates by year to expose changes in this selected population.

**Dependence.** Keep all signals for descriptive event counts, with one initial signal per episode as specified. A later trade simulation permits only one open position per product within a candidate policy; count suppressed overlaps. Bootstrap entire sessions for primary intervals and use calendar-week blocks as a dependence sensitivity. Preserve all anchors, timeframes, and paired policies together when resampling. For aggregate cross-product comparisons, preserve shared dates across products. Show session-weighted summaries alongside event-weighted summaries so very active days do not silently dominate.

**Chronological evaluation.** Proposed development period: each product's available history through 2023. Validation: 2024. Final evaluation: 2025 through September 18, 2026. Published whole-year metadata gives the following maximum eligible-day populations before any strategy filters:

| Product | Development through 2023 | Validation 2024 | Final 2025–2026 |
|---|---:|---:|---:|
| ES | 495 | 159 | 383 |
| NQ | 568 | 213 | 396 |
| GC | 512 | 62 | 251 |

Use GC's older years as explicitly labeled additional history and also show a common recent calendar period for comparability. Do not force granular GC validation results if too few events remain. These periods are proposed holdouts for this study; any previous examination of their relevant outcomes must be disclosed before claiming they were untouched. The checks used for this proposal did not calculate strategy outcomes.

Freeze definitions before viewing outcome tables. Keep a ledger of every candidate and variant inspected. For formal claims, declare the family of primary product × anchor × timeframe × candidate contrasts, and use a dependence-aware multiple-comparison adjustment or simultaneous bootstrap intervals. Treat the larger collection of tick thresholds and condition breakdowns as exploratory. Selecting from many variants can produce impressive historical results by chance; this motivates limited prespecified comparisons and a protected final evaluation ([Bailey et al., The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)).

## Planned report and limits of this proposal

The eventual report should open with a six-candidate scorecard and readable examples, followed by event counts, return-time curves, favorable/adverse movement distributions, baseline differences, year stability, and uncertainty. Tables should be exportable, and each result should point to its exact definition and sample. Any later implementation belongs in Sahadeva, with reproducible configurations, unique run IDs, and input hashes. No implementation directories or executable study files are created by this proposal.

The initial thresholds are proposals for discussion. The data inspection establishes availability and semantics, not an edge. Remaining decisions before an executable profitability study are the preferred initial product/window scope, economically meaningful target sizes, and execution/cost assumptions. They do not prevent defining or prioritizing these statistical studies now.

## Source and provenance record

The three supplied manifest hashes were checked on September 22, 2026 and matched exactly:

| Manifest | SHA-256 |
|---|---|
| 2m | `7ec9b9093cf12be856a976c1e41a3f7d8c29896b2e15c59cc46708694a7f9bff` |
| 5m | `32f79a14ecdb604fb132e00c6e9511b8323a4145ae52e57fba4a046bd4fc2310` |
| Release | `0fb21224a74a793c639d226b709e461c60064f53ccc8ec53c01dd456ea1eb495` |

This verifies the manifest files, not a new exhaustive checksum validation of every data partition. Sampled feature files covered each product/timeframe's 2026 partition, with limited rows from September 18 used to inspect types, tick sizes, feature availability, and anchor initialization. The unadjusted ES 2026 schema was also inspected. No applicable `AGENTS.md` was found in the checked project paths or Sahadeva's ancestor paths.

Authoritative local references:

- [Release manifest](../../catalog/datasets/session_anchored_vwap__1.0.0.release.json)
- [5m manifest and year coverage](../../catalog/datasets/session_anchored_vwap_5m_v1.json)
- [Schema](../../catalog/schemas/session_anchored_vwap__1.0.0.json)
- [Indicator definitions and membership windows](../../catalog/indicators/session_anchored_vwap__1.0.0.json)
- [Published quality report](../../reports/quality/session_anchored_vwap__1.0.0.md)
- [Maintained feature loader](../../packages/bhishma/src/abacus_bhishma/feature_loader.py)
- [Unadjusted source manifest](../../catalog/datasets/volume_lead_unadjusted_v1.json)

The Abacus Bhishma publication is read-only throughout this work.
