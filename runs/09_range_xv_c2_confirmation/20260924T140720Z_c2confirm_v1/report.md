# Does waiting for C2 improve a first countertrend reversal read?

Study `09_range_xv_c2_confirmation`; new long-history local run. All rates and price values below are selected from the saved numerical CSVs. This is a retrospective chart-behavior comparison, not an execution study.

## Answer

A C2 candle confirms the first countertrend C1 after 3+ prior trend bars in **73.8%–76.0%** of common eligible C1 opportunities. Once C2 confirms, the next **two** candles, C3 and C4, both follow in **40.3%–42.9%** of decisions across charts and directions. This is a later two-bar horizon than the C2+C3 outcome observed at C1.

The frozen candidate-versus-ordinary screen finds **8 of 70** positive chart/direction/session-window contrasts, with 65 cells meeting minimum support. The positives are concentrated in GC and bearish NQ 10RXV, usually about 1–2 percentage points above ordinary two-bar states. The post-result check against ordinary pairs that are also exactly two bars old reduces, but does not erase, those example differences. This age-matched check is exploratory and cannot validate the selected cells.

Waiting is selective: on the same original C1 opportunity set, the rate of an immediate two-bar directional success is **47.1%–49.6%**, while a C2 confirmation followed by **two additional** bars occurs **30.0%–32.6%** of the time. Waiting skips non-confirming opportunities and shifts the measured horizon by one bar. The signed open-to-open chart-price proxy for the wait policy is negative on average in every chart/direction. Its difference from the immediate proxy is negative in 11 of 14 chart/direction cases. These numbers do not show a profitable trade.

## Frozen definitions

C1 is the first non-doji bar opposite an uninterrupted prior run within one inferred 18:00 New York session. Main signals have at least three prior bars. C2 confirms only if it closes in C1's direction. At C2's strictly later next-bar-start completion proxy, ask whether C3 and C4 both close in that direction. C1 and C2 are excluded from those two future bars. A doji fails continuation. C1 through C4 must each have a strict within-session completion proxy, so C5's start is available for the price proxy. Equal-second and session/export-boundary cases are excluded, not counted as failures.

Ordinary B1/B2 pairs are adjacent same-direction non-doji bars observed at B2 completion, excluding the main C1/C2 candidate pairs. Their B3/B4 outcome uses the same strict completion rule. The baseline is matched within chart, direction, and decision-time window; it includes both early and mature ordinary runs. The exploratory age-two baseline restricts B2 to exactly bar two of its run. Neither comparison is causal.

The enhanced timestamps are already inferred New York wall time; no second conversion was applied. Half-open decision windows are Asia 18:00–03:00, London/pre-NY 03:00–09:30, NY morning 09:30–12:00, NY afternoon 12:00–16:00, and transition 16:00–18:00. Daylight saving is reflected in those stored wall times. ATAS timezone configuration remains unverified, so the labels are conditional on the clock interpretation.

## C2 decision: chart and direction baselines

Candidate and ordinary rates below share the C2/B2 decision horizon. Each candidate rate has a 95% session-cluster interval. The ordinary baseline and the difference are in the [full overall table](tables/overall.csv), with numerator, denominator, dates, events/date, both intervals, and the joint session-cluster difference interval. Charts remain separate because settings of one product share trades.

| Chart | C2 direction | C3 follows | C3+C4 both follow | Ordinary B3+B4 | Difference | Candidate dates; events/date |
|---|---|---:|---:|---:|---:|---:|
| ES 4RXV | bearish | 63.6% (39,864/62,680) [63.2%–64.0%] | 40.3% (25,276/62,680) [39.9%–40.7%] | 40.2% (115,222/286,697) | +0.14 pp [-0.29, +0.56] | 1,778; 35.3 |
| ES 4RXV | bullish | 63.7% (39,611/62,137) [63.4%–64.1%] | 40.8% (25,338/62,137) [40.4%–41.2%] | 40.6% (116,741/287,803) | +0.21 pp [-0.22, +0.65] | 1,773; 35.0 |
| ES 5RXV | bearish | 63.8% (28,498/44,661) [63.4%–64.2%] | 41.1% (18,343/44,661) [40.6%–41.5%] | 40.9% (85,611/209,270) | +0.16 pp [-0.37, +0.69] | 1,775; 25.2 |
| ES 5RXV | bullish | 63.7% (28,390/44,603) [63.2%–64.1%] | 41.2% (18,397/44,603) [40.8%–41.7%] | 41.1% (85,902/208,851) | +0.12 pp [-0.40, +0.63] | 1,765; 25.3 |
| ES 6RXV | bearish | 63.8% (21,283/33,352) [63.2%–64.4%] | 41.3% (13,767/33,352) [40.7%–41.8%] | 41.3% (65,245/158,156) | +0.02 pp [-0.57, +0.62] | 1,756; 19.0 |
| ES 6RXV | bullish | 64.3% (21,379/33,234) [63.8%–64.8%] | 41.6% (13,829/33,234) [41.1%–42.2%] | 41.7% (66,153/158,558) | -0.11 pp [-0.70, +0.48] | 1,747; 19.0 |
| GC 6RXV | bearish | 64.2% (43,795/68,215) [63.8%–64.6%] | 41.4% (28,268/68,215) [41.0%–41.9%] | 39.8% (113,479/285,002) | +1.62 pp [+1.21, +2.04] | 1,769; 38.6 |
| GC 6RXV | bullish | 64.7% (43,802/67,724) [64.3%–65.1%] | 41.8% (28,289/67,724) [41.4%–42.2%] | 40.9% (124,840/305,558) | +0.91 pp [+0.48, +1.35] | 1,771; 38.2 |
| GC 10RXV | bearish | 65.0% (21,696/33,397) [64.4%–65.5%] | 42.6% (14,229/33,397) [42.0%–43.2%] | 40.6% (58,055/143,048) | +2.02 pp [+1.38, +2.66] | 1,750; 19.1 |
| GC 10RXV | bullish | 65.3% (21,630/33,105) [64.8%–65.9%] | 42.9% (14,187/33,105) [42.3%–43.4%] | 41.8% (64,700/154,879) | +1.08 pp [+0.46, +1.70] | 1,740; 19.0 |
| NQ 10RXV | bearish | 63.9% (123,427/193,286) [63.6%–64.1%] | 41.0% (79,340/193,286) [40.8%–41.3%] | 39.6% (320,897/810,996) | +1.48 pp [+1.23, +1.73] | 1,783; 108.4 |
| NQ 10RXV | bullish | 63.8% (123,164/193,088) [63.5%–64.0%] | 41.0% (79,076/193,088) [40.7%–41.2%] | 40.3% (336,730/835,649) | +0.66 pp [+0.41, +0.91] | 1,782; 108.4 |
| NQ 20RXV | bearish | 65.0% (44,276/68,134) [64.6%–65.4%] | 42.3% (28,814/68,134) [41.9%–42.7%] | 41.8% (131,154/313,692) | +0.48 pp [+0.06, +0.90] | 1,771; 38.5 |
| NQ 20RXV | bullish | 65.0% (44,203/67,957) [64.7%–65.4%] | 42.7% (28,987/67,957) [42.3%–43.0%] | 42.4% (135,002/318,046) | +0.21 pp [-0.20, +0.62] | 1,766; 38.5 |

The [full overall table](tables/overall.csv) also has P(C4 follows | C3 followed), with its smaller conditional denominator and interval. The matched baseline has the analogous B4|B3 outcome. [Prior-run bins](tables/prior_bin.csv) retain the prespecified 3–4, 5–7, and 8+ candidate splits, and [bin opportunity counts](tables/prior_bin_opportunity.csv) preserve their original C1 denominators; these are descriptive and share the overall ordinary baseline.

## Decision-time session lookup

Each cell shows the candidate probability that C3 and C4 both follow C2 and its difference in percentage points from the ordinary two-bar baseline. The [full 70-cell comparison](tables/comparison.csv) records all numerator/denominator, dates, events/date, intervals, and baseline values; [period rows](tables/period.csv) show 2019–2021, 2022–2023, and 2024–2026 separately.

| Chart; C2 direction | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| ES 4; bearish | 40.7% (+0.82 pp) | 39.9% (-0.42 pp) | 40.5% (+0.34 pp) | 40.4% (+0.04 pp) | 38.9% (-0.69 pp) |
| ES 4; bullish | 41.3% (+0.56 pp) | 41.3% (+1.05 pp) | 40.7% (+0.10 pp) | 40.2% (-0.46 pp) | 41.1% (+0.62 pp) |
| ES 5; bearish | 40.6% (+0.04 pp) | 41.4% (+0.86 pp) | 41.5% (+0.43 pp) | 40.8% (-0.41 pp) | 38.6% (-1.09 pp) |
| ES 5; bullish | 41.9% (+0.60 pp) | 41.2% (+0.79 pp) | 41.4% (+0.30 pp) | 40.7% (-0.81 pp) | 42.1% (+0.71 pp) |
| ES 6; bearish | 41.3% (+0.50 pp) | 41.2% (+0.03 pp) | 41.0% (-0.14 pp) | 41.4% (-0.25 pp) | 43.4% (+2.69 pp) |
| ES 6; bullish | 42.1% (+0.61 pp) | 41.7% (+0.74 pp) | 41.9% (-0.07 pp) | 41.0% (-1.02 pp) | 41.9% (-0.95 pp) |
| GC 6; bearish | 40.8% (+1.03 pp) | 41.7% (+1.95 pp) | 42.0% (+1.90 pp) | 41.4% (+1.58 pp) | 42.1% (+3.29 pp) |
| GC 6; bullish | 41.5% (+0.35 pp) | 42.4% (+1.58 pp) | 41.9% (+1.08 pp) | 40.7% (+0.72 pp) | 43.0% (-1.42 pp) |
| GC 10; bearish | 42.6% (+2.32 pp) | 42.4% (+1.88 pp) | 42.7% (+2.01 pp) | 43.1% (+2.11 pp) | 40.6% (-2.61 pp) |
| GC 10; bullish | 43.0% (+1.12 pp) | 42.9% (+1.18 pp) | 42.9% (+1.15 pp) | 42.4% (+1.08 pp) | 43.2% (-3.05 pp) |
| NQ 10; bearish | 41.4% (+1.50 pp) | 42.2% (+1.43 pp) | 40.0% (+1.41 pp) | 41.3% (+1.73 pp) | 41.0% (+0.72 pp) |
| NQ 10; bullish | 42.0% (+0.93 pp) | 41.9% (+0.77 pp) | 39.6% (+0.33 pp) | 41.2% (+1.03 pp) | 40.2% (-1.34 pp) |
| NQ 20; bearish | 42.4% (+0.98 pp) | 42.5% (+0.92 pp) | 42.1% (+0.35 pp) | 42.3% (+0.16 pp) | 41.8% (-0.71 pp) |
| NQ 20; bullish | 43.5% (+0.73 pp) | 42.4% (+0.13 pp) | 42.7% (+0.47 pp) | 42.3% (-0.25 pp) | 41.9% (-0.91 pp) |

## Supported positive contrasts and run-age check

The prespecified positive screen requires at least 300 candidates, 100 session dates, and 2 candidates/date; a two-sided Bonferroni lower interval above zero across 70 contrasts; and positive differences in all three chronological periods with at least 30 candidate dates each. The post-result age-two comparison is shown for diagnosis with ordinary 95% intervals only. It was not in the frozen screen.

| Chart; C2; window | C3+C4 follows [95% CI] | Dates; events/date | Ordinary rate; Δ and familywise CI | Three period Δ (pp) | Age-two ordinary; Δ [95% CI] |
|---|---:|---:|---:|---:|---:|
| GC 6; bearish; London/pre-NY | 41.7% (8,737/20,977) [41.0%–42.3%] | 1,736; 12.1 | 39.7%; +1.95 pp [+0.70, +3.21] | +2.21, +1.73, +1.94 | 40.4% (8,215/20,355); +1.29 pp [+0.34, +2.24] |
| GC 6; bearish; NY morning | 42.0% (6,468/15,414) [41.2%–42.8%] | 1,712; 9.0 | 40.1%; +1.90 pp [+0.40, +3.40] | +3.38, +4.38, +1.18 | 40.6% (5,992/14,767); +1.38 pp [+0.26, +2.51] |
| GC 6; bullish; London/pre-NY | 42.4% (8,766/20,669) [41.7%–43.1%] | 1,723; 12.0 | 40.8%; +1.58 pp [+0.27, +2.89] | +2.13, +1.99, +1.42 | 40.5% (8,527/21,043); +1.89 pp [+0.90, +2.88] |
| GC 10; bearish; Asia | 42.6% (4,487/10,532) [41.6%–43.6%] | 1,296; 8.1 | 40.3%; +2.32 pp [+0.53, +4.12] | +2.07, +3.12, +2.29 | 41.1% (4,459/10,838); +1.46 pp [+0.17, +2.75] |
| NQ 10; bearish; Asia | 41.4% (13,267/32,030) [40.9%–42.0%] | 1,756; 18.2 | 39.9%; +1.50 pp [+0.48, +2.52] | +0.56, +1.77, +1.78 | 40.2% (12,683/31,556); +1.23 pp [+0.48, +1.97] |
| NQ 10; bearish; London/pre-NY | 42.2% (16,681/39,566) [41.6%–42.7%] | 1,765; 22.4 | 40.7%; +1.43 pp [+0.49, +2.37] | +1.46, +1.50, +1.39 | 41.0% (16,091/39,285); +1.20 pp [+0.50, +1.90] |
| NQ 10; bearish; NY afternoon | 41.3% (22,609/54,772) [40.8%–41.7%] | 1,753; 31.2 | 39.5%; +1.73 pp [+0.95, +2.52] | +1.23, +1.85, +1.90 | 39.9% (21,590/54,090); +1.36 pp [+0.79, +1.94] |
| NQ 10; bearish; NY morning | 40.0% (24,942/62,429) [39.5%–40.4%] | 1,766; 35.4 | 38.5%; +1.41 pp [+0.63, +2.18] | +0.69, +1.31, +1.88 | 38.7% (23,579/61,005); +1.30 pp [+0.73, +1.87] |

[All age-two results](tables/age2_comparison.csv), including negatives and sparse windows, are retained. GC and NQ positives are small relative to the roughly 40% ordinary two-more rate. ES shows no positive cell under the frozen screen. The periods are historical, and the recent years were already inspected in earlier RXV work; a new export is needed before treating any cell as a validated rule.

## What waiting costs per original C1

The following table keeps **every** strictly eligible main C1 in the denominator. C2 confirmation is the fraction for which the wait policy would act. Immediate success means C2 and C3 follow C1; wait success means C2 confirms and C3 and C4 follow. The horizons differ by one candle. Each cell shows numerator/denominator, rate, and 95% session-cluster interval; the dates and event density apply to the common C1 sample.

| Chart; C1 direction | C2 confirms | Immediate two after C1 | Wait confirms + two after C2 | Dates; C1/date |
|---|---:|---:|---:|---:|
| ES 4; bearish | 74.5% (62,680/84,167) [74.2%–74.8%] | 47.4% (39,864/84,167) [47.0%–47.7%] | 30.0% (25,276/84,167) [29.7%–30.3%] | 1,780; 47.3 |
| ES 4; bullish | 73.8% (62,137/84,174) [73.5%–74.1%] | 47.1% (39,611/84,174) [46.7%–47.4%] | 30.1% (25,338/84,174) [29.8%–30.4%] | 1,777; 47.4 |
| ES 5; bearish | 74.4% (44,661/60,005) [74.1%–74.8%] | 47.5% (28,498/60,005) [47.1%–47.9%] | 30.6% (18,343/60,005) [30.2%–31.0%] | 1,779; 33.7 |
| ES 5; bullish | 74.3% (44,603/59,991) [74.0%–74.7%] | 47.3% (28,390/59,991) [46.9%–47.7%] | 30.7% (18,397/59,991) [30.3%–31.0%] | 1,770; 33.9 |
| ES 6; bearish | 74.4% (33,352/44,828) [74.0%–74.8%] | 47.5% (21,283/44,828) [47.0%–48.0%] | 30.7% (13,767/44,828) [30.3%–31.2%] | 1,771; 25.3 |
| ES 6; bullish | 74.2% (33,234/44,791) [73.8%–74.6%] | 47.7% (21,379/44,791) [47.3%–48.2%] | 30.9% (13,829/44,791) [30.4%–31.3%] | 1,755; 25.5 |
| GC 6; bearish | 74.3% (68,215/91,811) [73.9%–74.7%] | 47.7% (43,795/91,811) [47.3%–48.1%] | 30.8% (28,268/91,811) [30.4%–31.2%] | 1,772; 51.8 |
| GC 6; bullish | 75.4% (67,724/89,808) [75.1%–75.8%] | 48.8% (43,802/89,808) [48.4%–49.2%] | 31.5% (28,289/89,808) [31.1%–31.9%] | 1,773; 50.7 |
| GC 10; bearish | 74.7% (33,397/44,733) [74.2%–75.1%] | 48.5% (21,696/44,733) [48.0%–49.0%] | 31.8% (14,229/44,733) [31.3%–32.3%] | 1,766; 25.3 |
| GC 10; bullish | 76.0% (33,105/43,584) [75.5%–76.4%] | 49.6% (21,630/43,584) [49.1%–50.1%] | 32.6% (14,187/43,584) [32.1%–33.0%] | 1,752; 24.9 |
| NQ 10; bearish | 74.2% (193,286/260,495) [74.0%–74.4%] | 47.4% (123,427/260,495) [47.2%–47.6%] | 30.5% (79,340/260,495) [30.3%–30.7%] | 1,783; 146.1 |
| NQ 10; bullish | 74.4% (193,088/259,432) [74.2%–74.6%] | 47.5% (123,164/259,432) [47.2%–47.7%] | 30.5% (79,076/259,432) [30.3%–30.7%] | 1,783; 145.5 |
| NQ 20; bearish | 74.7% (68,134/91,163) [74.4%–75.0%] | 48.6% (44,276/91,163) [48.2%–48.9%] | 31.6% (28,814/91,163) [31.3%–32.0%] | 1,776; 51.3 |
| NQ 20; bullish | 74.6% (67,957/91,115) [74.3%–74.9%] | 48.5% (44,203/91,115) [48.2%–48.9%] | 31.8% (28,987/91,115) [31.5%–32.1%] | 1,769; 51.5 |

C2 failures and dojis remain visible in [opportunity outcomes](tables/opportunity_overall.csv). That table also reports P(C3 returns to the original trend | C2 did not confirm), with its conditional numerator, denominator, session dates, event density, and interval. [C1-window](tables/opportunity_window.csv) and [period](tables/opportunity_period.csv) tables preserve the full opportunity-set counts.

## Two-bar chart-price movement and adverse excursion

Immediate uses C2 open→C4 open and C2/C3 extrema; wait uses C3 open→C5 open and C3/C4 extrema. These are chart references, **not fills**. The wait-per-C1 mean assigns zero movement to opportunities without confirmation. Mean signed ticks and its 95% session-cluster interval are shown below; the paired wait-minus-immediate interval uses each original C1. The [price table](tables/price.csv) includes medians, 5th-percentile movement, and mean/median/90th-percentile maximum adverse excursion for each policy. [Paired differences](tables/price_delta.csv) retain the exact mean and interval.

| Chart; C1 | Immediate mean ticks [95% CI] | Wait mean per C1 [95% CI] | Wait − immediate [95% CI] | Wait confirmed p05 ticks; median/90th MAE ticks |
|---|---:|---:|---:|---:|
| ES 4; bearish | -0.31 [-0.39, -0.23] | -0.48 [-0.54, -0.42] | -0.17 [-0.25, -0.08] | -15; 6/15 |
| ES 4; bullish | -0.42 [-0.51, -0.33] | -0.41 [-0.48, -0.35] | +0.01 [-0.08, +0.09] | -15; 5/15 |
| ES 5; bearish | -0.42 [-0.53, -0.30] | -0.47 [-0.55, -0.38] | -0.05 [-0.17, +0.07] | -18; 7/18 |
| ES 5; bullish | -0.43 [-0.55, -0.32] | -0.44 [-0.53, -0.36] | -0.01 [-0.13, +0.11] | -18; 7/18 |
| ES 6; bearish | -0.54 [-0.70, -0.38] | -0.51 [-0.63, -0.39] | +0.03 [-0.12, +0.19] | -21; 8/21 |
| ES 6; bullish | -0.47 [-0.63, -0.31] | -0.45 [-0.57, -0.33] | +0.02 [-0.15, +0.18] | -21; 8/21 |
| GC 6; bearish | -0.37 [-0.51, -0.23] | -0.55 [-0.65, -0.46] | -0.18 [-0.31, -0.06] | -24; 9/22 |
| GC 6; bullish | +0.14 [+0.01, +0.27] | -0.47 [-0.57, -0.38] | -0.62 [-0.74, -0.49] | -24; 8/22 |
| GC 10; bearish | -0.31 [-0.58, -0.03] | -0.59 [-0.81, -0.38] | -0.29 [-0.55, -0.03] | -37; 13/35 |
| GC 10; bullish | +0.53 [+0.28, +0.78] | -0.38 [-0.59, -0.17] | -0.91 [-1.19, -0.64] | -37; 13/35 |
| NQ 10; bearish | -0.59 [-0.70, -0.48] | -0.92 [-1.01, -0.84] | -0.33 [-0.44, -0.22] | -36; 13/34 |
| NQ 10; bullish | -0.51 [-0.63, -0.39] | -1.02 [-1.11, -0.93] | -0.51 [-0.63, -0.40] | -36; 13/34 |
| NQ 20; bearish | -0.62 [-0.97, -0.27] | -1.06 [-1.33, -0.79] | -0.44 [-0.78, -0.11] | -66; 24/64 |
| NQ 20; bullish | -0.77 [-1.11, -0.43] | -1.02 [-1.29, -0.76] | -0.25 [-0.59, +0.08] | -66; 24/64 |

A positive bar-count difference does not imply a price advantage. Medians on confirmed decisions are positive in many charts while mean signed ticks are negative, showing an unfavorable tail in this proxy. The data lack bid/ask, fees, slippage, exact completions, and intrabar order. The two policies also act at different times and have different exposure. No stop or target outcome is inferred.

## One-bar aligned snapbacks are a separate setup

For paired charts, the latest larger bar must have completed strictly before C1 and point in C1's direction; equal-second larger ties are excluded. One-bar aligned snapbacks have a higher C2 confirmation frequency, but their post-C2 two-more rates remain close to ordinary pairs. This secondary context must not be used as the first-reversal-after-3+ rate. [Full snapback estimates](tables/snapback.csv) include numerator, denominator, date count, event density, intervals, and ordinary baseline comparisons. [Equal-second tie sensitivity](tables/snapback_tie_sensitivity.csv) shows the same rates with ties included and for ties alone, using only the latest strictly prior larger state in every case.

| Pair; C1 direction | C2 confirms | C3+C4 follows after confirmation | Ordinary two-bar baseline |
|---|---:|---:|---:|
| ES 4; bearish | 79.0% (12,096/15,315) [78.4%–79.6%] | 40.1% (4,846/12,096) [39.1%–41.0%] | 40.2% |
| ES 4; bullish | 79.1% (12,076/15,267) [78.4%–79.8%] | 41.3% (4,983/12,076) [40.4%–42.1%] | 40.6% |
| ES 5; bearish | 79.2% (8,822/11,134) [78.5%–80.0%] | 40.0% (3,528/8,822) [39.0%–41.0%] | 40.9% |
| ES 5; bullish | 79.6% (8,821/11,076) [78.9%–80.4%] | 40.7% (3,586/8,821) [39.6%–41.7%] | 41.1% |
| GC 6; bearish | 78.2% (16,679/21,326) [77.7%–78.8%] | 39.6% (6,600/16,679) [38.8%–40.3%] | 39.8% |
| GC 6; bullish | 79.0% (18,170/22,995) [78.5%–79.6%] | 40.6% (7,376/18,170) [39.9%–41.3%] | 40.9% |
| NQ 10; bearish | 77.5% (46,269/59,702) [77.1%–77.9%] | 38.9% (17,992/46,269) [38.4%–39.4%] | 39.6% |
| NQ 10; bullish | 77.8% (48,077/61,819) [77.4%–78.1%] | 40.3% (19,356/48,077) [39.8%–40.7%] | 40.3% |

## Data audit, sensitivity, and traces

The pinned manifest and all source/enhanced hashes were checked before extraction. All seven enhanced files passed row count, session-date count, completion-status count, source-row continuity, nondecreasing start time, and OHLC checks. No bars were filled. The table shows counts after the five declared GC session exclusions; completion/boundary exclusions were counted before GC removal.

| Chart | Bars | Observed session dates | C1 signals | Main eligible C1 | C2 confirmed | Ordinary pairs | Main completion/boundary exclusions |
|---|---:|---:|---:|---:|---:|---:|---:|
| ES 4 | 1,281,962 | 1,783 | 408,694 | 168,341 | 124,817 | 574,500 | 30,219 |
| ES 5 | 885,222 | 1,783 | 281,003 | 119,996 | 89,264 | 418,121 | 16,764 |
| ES 6 | 647,911 | 1,783 | 205,195 | 89,619 | 66,586 | 316,714 | 10,276 |
| GC 6 | 1,661,279 | 1,780 | 516,993 | 181,619 | 135,939 | 590,560 | 71,422 |
| GC 10 | 737,194 | 1,780 | 229,181 | 88,317 | 66,502 | 297,927 | 23,046 |
| NQ 10 | 4,646,126 | 1,783 | 1,436,045 | 519,927 | 386,374 | 1,646,645 | 199,906 |
| NQ 20 | 1,343,643 | 1,783 | 415,188 | 182,278 | 136,091 | 631,738 | 25,804 |

Both GC charts lack 2021-04-02, 2023-04-07, and 2026-04-03 relative to ES/NQ; the files alone do not prove whether those dates were closed or omitted. The primary GC sample excludes 2026-01-28, 02-04, 02-20, 03-19, and 04-02 due to documented differences from older exports, including a major March 19 gap. [GC re-inclusion estimates](tables/gc_sensitivity.csv) change the aggregate candidate rates modestly; other differing GC overlap sessions remain a limitation. See the [long-history audit](../../../docs/range-xv-long-history-20260924.md), [checks](checks.json), [extraction audit](audit.json), and [input lock](inputs.lock.json).

Three ES 5RXV C1 events were reconciled with literal source and enhanced CSV rows, including C2–C4 direction and the two open-to-open price proxies when eligible:

| Session | C1 source row; prior run | C2/C3/C4 rows | Direction path | C2 confirms; later two succeed | C1/C2 completion wall time |
|---|---:|---:|---|---|---|
| 2019-11-04 | 55; 7 | 56/57/58 | 1x7,-1,1,1,1 | False; False | 2019-11-04 03:14:05; 2019-11-04 04:18:28 |
| 2019-12-05 | 1,250; 6 | 1251/1252/1253 | 1x6,-1,-1,-1,1 | True; False | 2019-12-05 07:18:15; 2019-12-05 07:36:33 |
| 2019-12-13 | 1,654; 5 | 1655/1656/1657 | 1x5,-1,-1,-1,-1 | True; True | 2019-12-13 08:41:21; 2019-12-13 09:06:43 |

The [trace table](tables/real_event_traces.csv) records source-row identities and signed ticks. The original ATAS clock is preserved as `source_timestamp`; the normalized wall time remains inferred from a fixed UTC−04 export-clock pattern, not independently confirmed ATAS settings.

## Inference and use

Each reported probability in the saved tables has its numerator, eligible denominator, distinct session-date count, events/date, and 95% session-cluster sandwich interval. Matched differences use a joint session-cluster score. The frozen headline family contains 70 candidate-versus-ordinary comparisons, corrected with two-sided Bonferroni intervals. Window-level support requires at least 300 candidates, 100 dates, and 2 events/date, plus a positive difference in all three historical periods with at least 30 dates. These are repeated historical reads, not independent experiments; chart settings of the same product and overlapping events remain dependent. The post-result age-two check is exploratory and unadjusted.

A fresh, genuinely unseen Range XV export with ATAS timezone, session, contract/roll, and feed settings verified is the next validation gate. The present result is a modest chart-state difference in GC and bearish NQ 10RXV, with no evidence that waiting improves a trade after price, costs, and execution are considered.

## Reproduction and retained evidence

The [run manifest](manifest.json) records exact commands, frozen settings, source snapshot, Git/environment identity, input hashes, exclusions, checks, and artifact hashes. The [event manifest](events.manifest.json) identifies the seven C1 opportunity ledgers and seven ordinary-pair ledgers retained in this run. All displayed outcomes derive from the saved numerical tables. This bundle is local research; no web publication was prepared.
