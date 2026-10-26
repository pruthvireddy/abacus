# Asia, London, and New York across the last three Range XV studies

Study `10_range_xv_session_overlay`. This is an exploratory overlay on immutable saved events from studies 07–09. Their samples and outcome horizons differ; none of the rates or tick means below are pooled across studies.

## Answer

**Study 07:** 0 of 27 candidate-price contrasts meets the exploratory segment screen after a two-tick round-trip haircut. Only 1 candidate segment has a positive net point estimate, and its familywise lower interval is below zero. No Asia, London, or New York price edge stands out.

**Study 08:** 3 of 42 chart/direction segments have a higher C2+C3 continuation rate than that chart and direction's other two named segments under the exploratory screen. All 3 are NQ 10RXV; the lifts are small. These are bar-count differences, not returns.

**Study 09:** 7 of 42 broad segments beat an ordinary same-direction two-bar pair on C3+C4 continuation. Only 1 also beats the confirmed candidate's other two segments after its separate familywise screen: NQ 10RXV bearish in London/pre-NY. Its C3+C4 rate is 42.16% (16,681/39,566), +1.43 pp above ordinary pairs and +1.41 pp above confirmed candidates in Asia plus New York. The wait-policy mean signed chart-price proxy remains negative in 42 of 42 named-segment chart/direction cells.

These are selected historical reads. NQ settings in studies 08 and 09 reuse underlying trades, and study 07's short history overlaps the long-history studies. The inferred ATAS/New York clock needs direct configuration verification; a fresh unseen export is required to validate a segment rule.

## Segment and inference rules

Use strict decision-time completion in inferred New York wall time: Asia 18:00–03:00; London/pre-NY 03:00–09:30; New York 09:30–16:00. The 16:00–18:00 transition is retained in each summary CSV but excluded from the three-way screen. These are half-open windows. Study 08 is grouped at C1 completion; study 09's confirmed/ordinary comparison at C2/B2 completion, while its per-original-C1 opportunity/price table uses C1 completion. Study 07's wait and early policies share the original signal's completion segment.

Minimum support is 300 candidate events on 100 session dates with at least two events/date. Each of three chronological blocks must have at least 30 candidate dates and a positive contrast for a standout. Session-cluster sandwich intervals use shared-date joint scores for contrasts. Separate two-sided Bonferroni families cover 27 study 07 idea/product/segment comparisons, 42 study 08 segment-vs-other comparisons, 42 study 09 candidate-vs-ordinary comparisons, and 42 study 09 segment-vs-other comparisons. The correction limits a search within each family, but does not turn previously inspected data into prospective confirmation.

## Study 07: chart-price payoff after two ticks

Each cell below is candidate mean net ticks per original opportunity, followed by its difference from the original same-idea control in ticks. The wait policy retains unconfirmed opportunities with zero return and no cost. [Complete summary](tables/07_summary.csv) gives opportunities, executed trades, dates, gross means, ordinary and familywise intervals, and transition rows; [development/validation/final rows](tables/07_period.csv) preserve stability and negative results.

| Product; idea | Asia net; Δ | London net; Δ | New York net; Δ |
|---|---:|---:|---:|
| ES; pullback | -2.01; -0.03 (1,509) | -2.50; -0.01 (1,898) | -2.16; +0.02 (6,023) |
| ES; exhaustion | -2.04; +1.43 (692) | -1.65; +0.11 (920) | -1.41; +0.60 (2,883) |
| ES; quiet breakout | -2.11; -0.54 (984) | -2.41; +0.36 (1,623) | -2.80; -0.46 (4,170) |
| GC; pullback | -1.61; +0.04 (2,338) | -1.16; +0.04 (1,755) | -2.19; +0.12 (2,247) |
| GC; exhaustion | -2.37; +1.20 (1,061) | +0.38; +1.95 (784) | -1.17; -0.35 (1,125) |
| GC; quiet breakout | -0.54; +1.06 (515) | -5.42; -2.85 (714) | -2.79; -0.20 (614) |
| NQ; pullback | -2.36; -0.16 (4,360) | -2.36; -0.06 (4,604) | -2.55; -0.08 (16,036) |
| NQ; exhaustion | -1.94; +1.81 (2,092) | -4.47; -2.46 (2,146) | -2.48; +0.87 (7,752) |
| NQ; quiet breakout | -0.86; +2.21 (1,775) | -4.35; -1.03 (2,773) | -3.35; -0.62 (7,390) |

The highest net point estimate is GC exhaustion in London/pre-NY: +0.38 ticks per opportunity. Its 27-comparison candidate net interval is [-5.46, +6.21] ticks; the candidate-minus-control family interval is [-4.35, +8.25] ticks. This does not pass the screen.

Study 07's saved payoff outcomes were computed on the earlier export-clock bytes. The [clock migration record](../../../docs/migration/range-xv-clock-normalization-20260924.json) documents that session dates and completion statuses did not change. This overlay joins each saved signal index to the same row in its current normalized enhanced file and uses only the corrected completion wall time for the segment label. The quiet-breakout cohort and half-hour calibration still reflect the old clock and need a separate corrected-clock study. The study 07 date span is shorter than studies 08/09.

## Study 08: first countertrend C1 after 3+ bars

The following rows passed the **exploratory** segment-vs-other screen for P(C2 and C3 both follow C1). Rates and differences use percentage points; the interval is corrected across 42 comparisons. [All chart/direction/segment rows](tables/08_summary.csv), [three periods](tables/08_period.csv), and [prior-run bins](tables/08_prior_bin.csv) include negative and unsupported cells.

| Chart; C1 direction | Segment | Successes/eligible | Rate | Versus other two segments [familywise CI] |
|---|---|---:|---:|---:|
| NQ 10RXV; bearish | London/pre-NY | 26,680/55,717 | 47.88% | +0.94 pp [+0.12, +1.76] |
| NQ 10RXV; bullish | Asia | 21,586/44,865 | 48.11% | +1.32 pp [+0.43, +2.21] |
| NQ 10RXV; bullish | London/pre-NY | 26,819/55,854 | 48.02% | +1.26 pp [+0.49, +2.03] |

NQ 10RXV is one chart setting, and its bullish/bearish segments share the same underlying trades. The selected differences are under two percentage points. No prior-run-length × session × direction cell passed study 08's original frozen 210-cell screen; this combined three-segment overlay answers a different, exploratory question.

## Study 09: C2 confirmation and ordinary two-bar pairs

Each cell shows P(C3 and C4 follow after C2 confirms) and its percentage-point difference from the ordinary B1/B2 baseline in that segment. [Full candidate and baseline table](tables/09_summary.csv) has counts, dates, uncertainty, segment-vs-other differences, and transition; [period rows](tables/09_period.csv) show chronology.

| Chart; C2 direction | Asia rate; Δ ordinary | London rate; Δ ordinary | New York rate; Δ ordinary |
|---|---:|---:|---:|
| ES 4; bearish | 40.66% (+0.82 pp) | 39.89% (-0.42 pp) | 40.45% (+0.19 pp) |
| ES 4; bullish | 41.31% (+0.56 pp) | 41.29% (+1.05 pp) | 40.45% (-0.18 pp) |
| ES 5; bearish | 40.64% (+0.04 pp) | 41.42% (+0.86 pp) | 41.16% (+0.01 pp) |
| ES 5; bullish | 41.91% (+0.60 pp) | 41.20% (+0.79 pp) | 41.06% (-0.26 pp) |
| ES 6; bearish | 41.30% (+0.50 pp) | 41.16% (+0.03 pp) | 41.24% (-0.20 pp) |
| ES 6; bullish | 42.13% (+0.61 pp) | 41.69% (+0.74 pp) | 41.44% (-0.55 pp) |
| GC 6; bearish | 40.83% (+1.03 pp) | 41.65% (+1.95 pp) | 41.75% (+1.78 pp) |
| GC 6; bullish | 41.51% (+0.35 pp) | 42.41% (+1.58 pp) | 41.42% (+0.93 pp) |
| GC 10; bearish | 42.60% (+2.32 pp) | 42.38% (+1.88 pp) | 42.87% (+2.05 pp) |
| GC 10; bullish | 42.97% (+1.12 pp) | 42.87% (+1.18 pp) | 42.73% (+1.12 pp) |
| NQ 10; bearish | 41.42% (+1.50 pp) | 42.16% (+1.43 pp) | 40.57% (+1.55 pp) |
| NQ 10; bullish | 42.01% (+0.93 pp) | 41.92% (+0.77 pp) | 40.37% (+0.65 pp) |
| NQ 20; bearish | 42.36% (+0.98 pp) | 42.55% (+0.92 pp) | 42.21% (+0.27 pp) |
| NQ 20; bullish | 43.54% (+0.73 pp) | 42.36% (+0.13 pp) | 42.56% (+0.15 pp) |

The rows passing the candidate-vs-ordinary familywise and three-period screen are:

| Chart; direction | Segment | Successes/decisions | Δ ordinary [familywise CI] | Δ other segments [familywise CI] | Segment-specific? |
|---|---|---:|---:|---:|---|
| GC 6; bearish | London/pre-NY | 8,737/20,977 | +1.95 [+0.75, +3.16] pp | +0.32 [-0.96, +1.60] pp | no |
| GC 6; bearish | New York | 10,581/25,346 | +1.78 [+0.70, +2.86] pp | +0.51 [-0.73, +1.74] pp | no |
| GC 6; bullish | London/pre-NY | 8,766/20,669 | +1.58 [+0.33, +2.84] pp | +0.95 [-0.39, +2.30] pp | no |
| GC 10; bearish | Asia | 4,487/10,532 | +2.32 [+0.61, +4.04] pp | -0.05 [-1.96, +1.87] pp | no |
| NQ 10; bearish | Asia | 13,267/32,030 | +1.50 [+0.52, +2.48] pp | +0.45 [-0.57, +1.46] pp | no |
| NQ 10; bearish | London/pre-NY | 16,681/39,566 | +1.43 [+0.53, +2.33] pp | +1.41 [+0.45, +2.36] pp | yes |
| NQ 10; bearish | New York | 47,551/117,201 | +1.55 [+1.00, +2.10] pp | -1.26 [-2.07, -0.44] pp | no |

For the one segment-specific row, the other-segment differences in 2019–2021, 2022–2023, and 2024–2026 are +1.17, +1.55, +1.42 pp. These periods were previously inspected. The corresponding ordinary-pair differences are +1.46, +1.50, +1.39 pp.

The post-result run-age diagnostic restricts ordinary B2 bars to exactly bar two of their run. In the selected London/pre-NY row, that ordinary baseline is 40.96%, leaving a +1.20 pp candidate difference with an ordinary 95% session-cluster interval [+0.50, +1.90] pp. [All run-age-two segment rows](tables/09_age_two.csv) are retained. This restriction was introduced after study 09's primary result and does not validate the selected segment.

### Common original C1 opportunity and chart-price check

At NQ 10RXV bearish C1 decisions in London/pre-NY, the immediate C2+C3 directional success rate is 48.25% (25,488/52,821); confirmation plus C3+C4 is 31.54% (16,658/52,821) per original C1. They are different two-bar horizons. The immediate open-to-open proxy averages -0.20 ticks per C1 [-0.43, +0.03], while the wait proxy, assigning zero to unconfirmed C1s, averages -0.59 ticks [-0.78, -0.41]. The paired wait-minus-immediate mean is -0.39 ticks [-0.64, -0.15]. [All segment opportunity and price rows](tables/09_opportunity.csv) are retained. These are unadjusted chart references, not fills or strategy returns.

## Audit and use

The [checks](checks.json) pass for 34 pinned files, including sealed event ledgers and the normalized short-history clock files. Nine study 07 signals were spot-traced to corrected source rows; full event-row, source-clock, session-date, and strict-completion identity were checked during mapping. Study 07 whole-cohort payoff arithmetic reconciles to its original report tables; 08 and 09 session totals, chronological rows, and 09 price means reconcile to their sealed saved tables. [Extraction audit](audit.json) records mapped counts and traces; the [input lock](inputs.lock.json) and [run manifest](manifest.json) record identities and artifact hashes.

GC export gaps and differing 2026 sessions remain as disclosed by studies 08/09. The ATAS timezone, feed, and contract settings were not independently verified. Session labels are conditional on the documented clock inference. A fresh, unseen export with those settings verified is the next validation gate; study 07's quiet-breakout condition also requires a corrected-clock rerun before a session claim about that idea.

Source evidence: [study 07](../../07_range_xv_edge_candidates/20260924T004900Z_rxv07/report.md), [study 08](../../08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/report.md), and [study 09](../../09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/report.md). This bundle is local research and was not published to a website.
