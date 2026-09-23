# Methodology

## Documented facts

- ATAS documents range charts as price-movement-based rather than fixed-time charts. Its current chart-types page lists RangeX, RangeXV, RangeUS, and RangeZ. It says the exact construction algorithms are not disclosed: https://help.atas.net/en/support/solutions/articles/72000602350
- ATAS describes Range XV as forming consecutive candles during directional movement and opposite-colored candles when counteraction appears, while keeping the construction method closed: https://atas.net/blog/specific-of-the-range-xv-chart/
- CME standard-contract units used here are ES 0.25 point/$12.50 per tick, NQ 0.25 point/$5 per tick, and GC $0.10 per troy ounce/$10 per tick: https://www.cmegroup.com/trading/equity-index/eminifaq.html, https://www.cmegroup.com/trading/equity-index/files/emini-nasdaq-100-futures-options.pdf, https://www.cmegroup.com/trading/metals/files/fact-card-gold-futures-options.pdf

## Observed behavior

The exports are headerless, semicolon-delimited, five-column files consistent with timestamp/open/high/low/close. The configured day-month timestamp parser succeeds for all rows. Price values align with the verified exchange tick sizes, OHLC inequalities are valid, row timestamps do not regress, and repeated timestamps are common. Geometry findings describe the exports only and do not infer the proprietary bar algorithm.

Observed timestamp gaps are reported by export date but are not classified as missing data. A quiet interval in a price-based chart can be legitimate, and the exports contain no feed-status or exchange-calendar field that would support a stronger conclusion.

## Frozen definitions

- Direction is `sign(close-open)` in integer exchange ticks. Dojis have direction zero and break runs.
- A reversal is the first non-doji bar immediately opposite the preceding non-doji bar in the same valid segment. Primary prior-run minimum is one; at-least-two and at-least-three are prespecified sensitivities.
- `L` counts subsequent same-direction bars and excludes the reversal; `T=1+L` includes it. The primary metric is `P(L>=3)`.
- A threshold estimate includes only signals with that many subsequent valid bars in the same segment. Boundary cases are exclusions, not failures. A shared N10 cohort supports continuation curves and `E[min(L,10)]`.
- Natural runs reaching a segment boundary without a breaking bar are right-censored. Completed-run summaries exclude their lower bounds.
- MAE/MFE reference the signal close and use subsequent bars only. Fixed horizons are 1/3/5/10/20 bars. Long and short formulas are symmetric. Through-break includes the break bar; run-only excludes it and is hindsight-conditioned.
- Provisional export-calendar dates define segments. The 60/20/20 split is development 2026-06-14–2026-08-02, validation 2026-08-04–2026-08-18, and test 2026-08-20–2026-09-04. Export dates 2026-08-03 and 2026-08-19 are embargoed.
- The development leader is frozen before reading test conclusions. Validation checks whether it retains the largest point estimate with at least 200 eligible reversals and 10 export dates. A clear held-out winner must retain the lead and beat every alternative under Holm-adjusted paired date-block tests.
- Dependence-aware intervals use 2,000 paired export-date bootstrap replicates with seed 20260906; three-date circular blocks are the multi-session sensitivity.

## Unresolved assumptions and unsupported analyses

The chart identity remains provisional filename-labeled Range XV, not verified Range XC. Timezone, timestamp meaning, bar-completion field, ATAS version/settings, data feed, continuous-contract/adjustment history, and whether prices are synthetic remain unresolved. The final export row is conservatively excluded. Raw timestamp differences are proxies only; no exact elapsed-time, official-session, intrabar ordering, extreme-touch time, common clock-horizon, volatility-normalized, or nominal-range-normalized claim is made. GC20 is missing and GC6 is not substituted.
