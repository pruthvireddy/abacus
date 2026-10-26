# VWAP state dynamics — implementation plan

Status: **planning only**. No events, outcomes, models, or reports have been computed for this study. A later user request must authorize implementation and execution. This study is distinct from the completed [session-anchored VWAP study](../05_session_vwap/README.md); its sealed runs and the pinned Bhishma publication are immutable.

## Purpose and scope

Estimate interpretable probabilities of future price behavior from information known about the **developing VWAP state**, including ordinary periods near VWAP. The initial investigation has three primary questions:

1. Does persistent time on one side of VWAP predict continued residence on that side, beyond current distance and clock time?
2. Does disagreement between the preceding price slope and VWAP slope predict a change of side?
3. Does volume weighting make the current VWAP a better reference for the next 30 minutes than an equal-weighted mean of the same completed bars?

Every reported result must read as an explicit conditional statement: population and clock, observable condition **X**, future event **Y**, horizon, numerator/denominator, uncertainty, and comparison. Probabilities of a path event are not trading win rates. No orders, fills, costs, sizing, or net profitability are specified here.

The already-viewed 2024 and 2025–2026 VWAP outcomes are **not untouched holdouts**. All results on currently pinned dates are exploratory, even when the new protocol is frozen before the new calculations. Confirmation requires a later, genuinely uninspected data period and a protocol frozen before that period is reviewed.

## Inputs and ownership

- Primary products: ES, NQ, GC. Use the pinned `session_anchored_vwap__1.0.0` release and its 2-minute features through Bhishma's public loader, plus the pinned unadjusted one-minute source for future price paths. Copy the exact manifest identities into this study's input lock; verify consumed partition hashes. Resolve storage through Abacus path configuration.
- The published VWAP weights each **completed output-bar HLC3** by that bar's volume. The comparison TWAP must be the cumulative equal-weighted HLC3 of the **same** completed output bars, with the same anchor reset and availability. Verify that recomputing the weighted series reproduces the published VWAP within declared numerical tolerance. Neither series is an exact trade-price VWAP.
- Study-specific derived features, labels, and code belong under `studies/06_vwap_state_dynamics/`; reusable Bhishma publication work needs a separate request. Never alter the published 1.0.0 release, study 05, or a sealed run.
- Use adjusted bars for causal price-reference features. Translate reference levels to the matching unadjusted contract coordinates for one-minute path outcomes, reconciling product, session date, raw symbol, instrument ID, adjustment, and roll. Report missing or discontinuous joins separately.

## Population and sampling

The primary cohort uses the **Globex anchor on 2-minute bars** throughout eligible product sessions. This gives one anchor view per product-time landmark. Label local clock windows, including the gaps between local membership windows; do not pretend all landmarks belong to NY, London, or Asia.

Choose regular half-hour landmarks on the New York local clock, including daylight-saving changes. A landmark is the exclusive close of a completed 2-minute bar. Require (a) at least 30 minutes of mature anchor history **before** the 30-minute feature lookback, (b) an exact, consecutive 30-minute lookback, and (c) complete 30-minute prospective coverage before the Globex session closes. Thus the first primary Globex landmark is no earlier than 19:00 after the 18:00 anchor start. Report all exclusions and the fraction of eligible product-days with landmarks. Each landmark's features use only bars with `available_at <= landmark_time`.

Separate replication cohorts, never pooled as independent observations: the local Asia, London, and NY anchors in their own membership windows, starting only after the same maturity-plus-lookback requirement; the independently calculated 5-minute release as a timeframe sensitivity. A local NY landmark can first qualify at 10:30 under this rule. Do not silently replace missing clock minutes or use a complete-day flag as a live signal; published day eligibility is retrospective.

Count both landmark-weighted and product-session-weighted outcomes. Preserve product and calendar date identifiers because nearby landmarks, products on the same date, anchors, and timeframes are dependent.

## Feature-only feasibility gate and protocol freeze

Before reading **any new future-outcome summaries**, inspect only feature availability, distributions, class counts, clock coverage, contract joins, and input checks. Choose and record minimum nonflat-slope and material-VWAP/TWAP-dislocation thresholds from **development-period feature distributions alone**. Small adjustments to the illustrative state cutoffs below are permitted solely for feature-class feasibility at this gate; log the initial and final cutoffs and the reason. Then freeze a versioned executable protocol, cohort definitions, primary comparisons, and report schema. Do not change a cutoff because a later outcome looks better.

Keep any extra segment discovered after outcome inspection in a separately labeled exploratory family. Record negative, null, and abandoned variants, not just favorable rows.

## Primary question 1 — residence and crossing state

At each landmark, compare the last 15 completed 2-minute closes with their **then-available** Globex VWAPs. Store fraction above, fraction below, equality count, number of completed-close side changes, current side, current signed distance in ticks and sigma, and maximum continuous same-side run. A crossing is a completed-close side change; a wick through VWAP is a separate event.

Illustrative feature states to freeze at the feature-only gate:

- **Persistent above/below:** at least 12 of 15 closes on the current side and at most one side change.
- **Rotational:** 6–9 of 15 closes above and at least three side changes.
- **Other:** every valid landmark not in either group. Report this denominator rather than dropping it.

Primary `Y1`: no completed close on the opposite side of the **causally updated** VWAP during the next 30 elapsed minutes. Crossing by exactly the horizon boundary counts as failure of residence; a missing future bar makes the outcome unavailable, not false. Report the corresponding first-cross time and a sensitivity against the **frozen landmark VWAP** to expose reference movement. Report `P(Y1 | persistent)`, `P(Y1 | rotational)`, and their difference, with current-side and product breakdowns.

Compare like with like on current side, absolute VWAP distance, product, time-of-day window, prior-only ATR regime, and anchor age. Report overlap and unmatched counts; show raw and context-adjusted differences separately. If overlap is weak, report that limit rather than extrapolating.

## Primary question 2 — price/VWAP slope disagreement

At each landmark calculate the adjusted-close change and Globex-VWAP change over the preceding exact 30 minutes, separately normalized by prior-day ATR or current available sigma. Classify **aligned**, **opposing**, and **flat/unavailable** using minimum absolute-movement thresholds frozen at the feature-only gate. Record signed magnitudes and VWAP acceleration descriptively. Do not infer order flow from OHLCV.

Primary `Y2`: an opposite-side completed-close crossing of causally updated VWAP within the next 30 minutes. Estimate `P(Y2 | opposing)` versus `P(Y2 | aligned)` and the difference. Compare within current price side, absolute VWAP distance, residence/crossing state, product, local clock, ATR regime, and anchor age, with overlap reported. `Y2` is the complement of `Y1` only for fully observed landmarks with a defined current side; reconcile those counts exactly.

Secondary path outcome for questions 1 and 2: from the following unadjusted one-minute open, did an **8-tick move in the current-side direction** occur before an 8-tick move in the opposite direction within 30 minutes? Preserve favorable-first, adverse-first, neither, and same-minute-order-ambiguous classes. Report the same events at a ceiling-rounded `0.5 × landmark sigma` barrier as a sensitivity, separately by product; never choose a winning barrier after looking at results.

## Primary question 3 — volume weighting versus equal weighting

At every landmark calculate the anchored TWAP from the same completed bars and anchor as published VWAP. Record `VWAP - TWAP`, both distances from current price, cumulative volume, recent-volume share, and anchor age. Report ties and near-identical references; do not treat them as evidence favoring either reference.

Primary future target: the median of the next 30 **unadjusted one-minute closes**, expressed in the same contract price coordinates as both landmark references. This is an ex-post target, never a signal feature. For each common landmark, compare absolute errors of frozen `VWAP_t`, frozen `TWAP_t`, and the last known price. Primary probability is `P(|future_median - VWAP_t| < |future_median - TWAP_t|)` with ties explicit. Also report the paired mean/median error difference and `P(VWAP wins)` when the two references are materially separated under a feature-only threshold. A future-volume-weighted 30-minute price and horizon-end close are secondary targets; the unweighted median avoids defining the primary target with the same weighting used by VWAP.

This is a **paired comparison at identical timestamps**, so there is no event-selection advantage for one reference. A better forecast reference still does not by itself define an executable trade.

## Secondary exploratory modules — separate tables, no promoted edge

Prioritize only after the three primary questions are reported:

1. **Volume shock and VWAP inertia:** recent completed 5/15-minute volume relative to a same-clock profile estimated from prior sessions, divided by already accumulated anchor volume; estimate next-15-minute VWAP displacement and whether price or the VWAP closes the gap. Historical profile must exclude the signal day and all later days.
2. **Local-session handoff:** at 10:30 NY time compare mature NY and Globex VWAPs, their separation and slopes, price location, and opening balance. Estimate which reference price reaches first by a fixed noon/NY-close deadline. Use one state per product-day and report already-passed references.
3. **Prior-session VWAP:** freeze the preceding eligible session's closing Globex VWAP and compare it with today's developing VWAP at fixed landmarks. Estimate first contact by noon or window end; handle rolls, missing prior dates, and price translation explicitly.
4. **Rolling versus anchored VWAP:** derive a completed-bar 30- or 60-minute rolling VWAP, record its separation/cross relative to Globex VWAP, then estimate future side persistence or first fixed-price contact. Do not use the same lookback bar twice when defining availability.
5. **VWAP within completed range:** locate VWAP within the completed session high/low and opening balance, then estimate subsequent VWAP contact versus a new range extreme. Use a prespecified matched-distance comparison.

These modules are **not** five additional primary tests. Freeze each in an amendment or separate run before its own outcomes are calculated. Trade-level volume-at-price, aggressor side, exact transaction-price VWAP, and true order flow require new source data; one-minute OHLCV supplies at most bar-based proxies.

## Estimation and validation

- For every probability, retain the complete funnel: eligible product-days → landmarks → feature-valid states → outcome-capable landmarks → favorable/cross/no-cross/neither/ambiguous/missing. Show event and distinct product-session counts, state coverage, and year/split rates.
- Preserve development through 2023, 2024 validation, and 2025–2026 chronological final labels from study 05, while explicitly marking **all currently observed periods exploratory**. Product coverage is discontinuous; do not force a common-day denominator except for a labeled cross-product analysis.
- Compute 95% uncertainty with whole **shared calendar dates** resampled across products and all correlated views. Include a product-session weighting sensitivity and, if a formal three-question family claim is attempted, a declared dependence-aware simultaneous or multiple-comparison procedure. Otherwise describe differences without a superiority claim.
- Report probability calibration and proper scores only if a small predictive model is later added. A baseline model using product, clock, current distance, and ATR must be compared before claiming that occupancy, slope, or volume features improve prediction. Train thresholds and model parameters only on development dates; 2024 and 2025–2026 remain chronological diagnostics, not protected confirmation.
- Show ES, NQ, and GC separately before any pooled estimate; report local clock, direction, anchor age, and yearly stability. Avoid an exhaustive interaction search. Use exact probability statements with denominators, not rankings by a cell's highest historical percentage.
- Reconcile adjusted reference levels against unadjusted execution prices, signal availability, session/contract continuity, and the VWAP/TWAP identity. Review deterministic examples for every outcome class and product. Tests should include daylight-saving clock boundaries, anchor resets, equality at VWAP, incomplete lookback, future-bar gaps, ties in reference accuracy, and intraminute barrier ambiguity.

## Execution order and deliverables for an authorized future task

1. Read repository and Sahadeva guides, study 05 plans/protocols/runs, and the pinned input lock. Create study 06 metadata and a distinct input lock; do not reclassify old results.
2. Implement a **feature-only pilot** and audit coverage without inspecting future outcomes. Freeze the executable protocol and notes with exact thresholds and three primary comparisons.
3. Implement landmark extraction, causal features, common outcomes, and focused numerical tests. Smoke-test one real product-day and independently reconcile at least one VWAP/TWAP sequence and one price path.
4. Run the complete pinned sample under a unique staged `work/06_vwap_state_dynamics/<run-id>/` directory. Audit identities, denominators, missingness, and parent release checksums; calculate primary tables before secondary exploratory modules.
5. Produce event-linked Parquet evidence, stable-ID CSV/JSON tables, uncertainty intervals, chronological and product breakdowns, figures, `report.md`/`report.html`, and dated `advice.md`. A concise probability atlas should state X, Y, horizon, numerator, denominator, baseline, interval, and interpretation for each row. Include negative and inconclusive results.
6. Verify focused tests, exact input hashes, source availability, example paths, report references, and artifact hashes. Save frozen settings, source/dirty snapshot, dependency lock identity, exact commands, and exclusions. Seal once at a unique `runs/06_vwap_state_dynamics/<run-id>/`; update the research index. Prepare any optional local Narada source before sealing, but do not publish a public bundle or deploy without explicit scope.

The first run's decision should identify whether any state feature improves a **like-for-like probability estimate** over distance, time, and volatility alone. It must not convert an exploratory conditional rate into a claim of profitable execution. [White's data-snooping analysis](https://onlinelibrary.wiley.com/doi/10.1111/1468-0262.00152) explains why a small frozen family and later uninspected confirmation matter.
