# Research advice — 2026-09-23

Run `05_session_vwap/20260923T035300Z_ac_context` applies exploratory protocol 1.1.0 to the unchanged A and C events from `20260923T015900Z_vwap3`. All rates below are favorable half-sigma movement before equal adverse movement within 30 minutes, from the next unadjusted one-minute open, unless stated otherwise. The final chronological period was previously viewed; these cuts provide discovery evidence, not protected confirmation or net return estimates.

## A — New York clock and exit context

**Finding:** For Globex VWAP observed in the NY window, first-hour 2σ exits had a 48.7% favorable-first rate in 2,260 full-follow-up events, versus 42.4% in 4,131 events after the first hour. The primary result therefore does not support the proposed weaker early exits. On the common fixed 8-tick barrier, first-hour was 28.5% versus 35.2% later, reversing the ordering. These are conditional rates among exits, not probabilities of an exit occurring. See [NY table](tables/ny_early.csv), [clock-matched controls](tables/control_comparisons.csv), and [report](report.html).

**Structural limit:** The NY-local VWAP has no eligible first-30-minute A signal under the 30-minute anchor warm-up. Its first-hour rate (minutes 30–59) is 46.0% in 2,897 events versus 45.8% later. Globex and NY-local anchors should not be pooled when interpreting the opening half-hour. [NY table](tables/ny_early.csv).

**Other cuts:** Stronger exits did not produce a consistent advantage: 2–2.25σ exits were 46.3% at the primary barrier and 40.3% at 8 ticks; 2.75σ+ exits were 46.7% and 36.6%. Prior ATR, opening-balance width and location, prior trend, sigma expansion, VWAP slope, and local/Globex geometry are retained in [all cuts](tables/cuts.csv) and [interactions](tables/interactions.csv). Context-matched 1–2σ controls still lack overlap in starting distance, and pooled A's apparent +1.9 point half-sigma difference becomes −1.3 points at 8 ticks. [Controls](tables/control_comparisons.csv).

**Decision:** Do not filter or trade A by NY first hour, exit distance, ATR, or opening balance based on this exploratory grid. The half-sigma/8-tick reversal makes a barrier-size and session-volatility explanation plausible; it does not identify a stable trading edge. Any new filter needs a fixed barrier and an untouched prospective evaluation period.

## C — Excursion before first touch

**Finding:** A pre-touch maximum completed-close excursion of 2σ+ yielded a 45.6% primary bounce rate in 55,673 full-follow-up events. The 1–1.5σ and 1.5–2σ groups were 47.2% and 47.8%; their 8-tick rates were 40.5%, 41.1%, and 40.0%, respectively. Larger prior moves therefore did not identify a better bounce. The touching bar was excluded when measuring the prior peak. [All cuts](tables/cuts.csv), [report](report.html).

**Return shape:** Within the 2σ+ group, a peak-to-touch interval of at most 15 minutes yielded 47.6% favorable first, versus 45.0% for a slower return. The 8-tick result reversed slightly, 39.0% versus 40.2%. Departures returning to touch in 16–45 minutes had a 49.2% primary rate versus 44.0% after more than 45 minutes, but fixed 8-tick rates were both near 40–41%. [Interactions](tables/interactions.csv), [all cuts](tables/cuts.csv).

**Baseline limit:** The saved C near-approach control cannot be matched on the same departure/peak history. The new shape cells are within-C associations, not incremental effects of touching VWAP. [Controls](tables/control_comparisons.csv).

**Decision:** Do not promote a large-excursion or fast-return C rule. A future causal comparison would need departure-linked near approaches and a prespecified fixed barrier, followed by fresh data.

## Re-entry after A

Of 90,938 original A exits, 89,475 (98.4%) published a first close back inside the same 2σ band. Of those, 84,997 had a full 30-minute follow-up; 38,909 (45.8%) reached the favorable half-sigma barrier first. Another 1,463 never confirmed and 4,470 confirmed too late for the full horizon. This is a later-signal conditional statistic. A policy comparison over **all** initial A episodes with a shared deadline, missed opportunities, fills, and costs remains necessary. [Re-entry table](tables/reentry.csv).

## Limits and next test

Events across anchor/timeframe views share product-session paths. Shared-date bootstrap intervals describe sampling variation but do not correct the many exploratory cuts. Day completeness is a retrospective eligibility condition. Execution costs, fill mechanics, latency, and overlap are unmodeled. The most useful next test is a small, frozen candidate set on untouched future data: a single A clock rule, a single C pre-touch shape rule, and a full-denominator immediate-versus-wait re-entry policy, each compared under the same executable price barriers. Retain these negative and inconclusive cuts in the research record.
