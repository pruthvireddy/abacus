# NQ Overnight Range at the Cash Open

Protocol 1.0.0. One observation per NQ trading session. Measure how overnight width, the 09:30 New York open and completed VXN/VIX context relate to regular-session boundary reaches. Compare the Instagram reel's reported upper-half high and lower-half low rates of 80.8% and 75.7% as attributed benchmarks on a different sample. Use no trade fills or P&L.

## Inputs and eligibility

Use hash-pinned same-contract, unadjusted NQ one-minute data and pinned Daily Facts and TradingView daily context. At New York local time use previous evening 18:00 to 09:30 and same-day 09:30 to 16:00, both half-open by minute start. CME's [historic contract hours](https://www.cmegroup.com/trading/equity-index/files/emini-nasdaq-100-futures-options.pdf) and [2021 rule change](https://www.cmegroup.com/notices/electronic-trading/2021/06/20210621.html) place the historical 16:15–16:30 pause outside both windows. Use the pinned holiday exclusions, validate exact minute grids and the published roll schedule, and report coverage separately before and after June 28, 2021. Do not override the Daily Facts v1 full-session eligibility rule. No interpolation for gaps. Published month/contract rolls are permitted only on verified single-contract windows.

The reusable Bhishma companion stores opening geometry, context, counts and status. VXN and VIX use latest completed values by 09:30 with a seven-day stale limit, preserving observation timing. Overnight features are logically available at 09:30. Open-derived fields are available at 09:31 on the completed-minute convention. Historical provider vintages are unverified. Primary outcome eligibility requires two complete windows and an open strictly between the levels. Midpoint ties remain in high/low summaries. A unique near side requires unequal distances. Opening exactly at or outside a boundary and degenerate ranges are counted separately.

## Themes and question map

| Theme | Questions | Evidence and denominator |
|---|---|---|
| Overnight range | Coverage and opening location. How wide is the range? | Coverage table, opening location and point-width distributions on available qualifying windows |
| Range size & volatility | How wide is the range by VXN or VIX? How unusual is it? How far does price move after the open? | Same-date volatility comparisons, prior-60 eligible window median excluding today, and first-hour/full-day movement by width and VXN |
| Touch rates | Do upper and lower halves resemble the reel? How do near-only, far-only, both and neither vary with width? What happens in narrow/high-VXN and wide/low-VXN groups? | Rates and session counts, width stacks and width by VXN matrices, including rates standardized to common near-distance groups where supported |
| First touch & path | Which side is first? How fast? How far against the near side before reaching it? What remains after 09:31? | First-minute event labels, cumulative reaches through 15, 60 and 390 minutes, excursion with hit-minute order bounds, and fresh-touch denominators |
| Beyond proximity | Do overnight levels outperform levels at the same distances on other paths? Does VXN or VIX add held-out information? | Matched prior-path replay by opening side, era, VXN regime and year proximity. Compare distance-only and index models on identical holdout rows using Brier loss and calibration |
| Era & yearly stability | How do 2015–2019 and 2020 onward compare? Does it hold annually in 2023–2026? | Counts, width, touch/order rates and supported width by VXN comparisons. Report 2018–2019 separately and compare recent years through September 18 as well |

## Rules frozen before outcome inspection

- Retain the January 2015 to September 18, 2026 roster. Development uses qualified modern-era sessions through 2024. Holdout begins January 2025. Use development tertiles rounded to whole 10 NQ points for width and whole index points for VXN/VIX, with exact intervals in saved settings. The historical comparison applies those same fixed thresholds. Below 25 observations in a displayed comparison cell, show support and suppress heatmap rate shading.
- Count a threshold as reached once a minute high is at or above the upper boundary or its low at or below the lower boundary. This includes bars that open through a boundary and is not tick-level execution evidence. First minute covering both levels makes order unresolved. A missing or unqualified outcome stays undefined.
- Quantify fresh touches starting with the 09:31 minute among sessions where the relevant boundary was untouched in the 09:30 minute. Denominators are target-specific. For excursions, measure against the 09:30 open. Bound the touch-minute ambiguity between excursion up to the touch-bar open and excursion including the full touch bar. No-target cases report full-session adverse movement separately.
- Use two-sided 95% Wilson intervals as descriptive per-session uncertainty. For paired held-out Brier differences use a five-session moving-block bootstrap with fixed seed. Model near-first and both-side outcomes with an L2-penalized logistic model. Exclude unresolved order only from the near-first model, record how many, and preserve neither as a valid negative. Use the same rows across model comparisons.
- Replay the original signed target distances on up to 20 nearby-in-time prior sessions sharing opening side and VXN band, at least five, excluding the target date. Report paired observed/placebo rates and donor coverage. This is a conditional comparison and can retain time/regime confounding.
- Inspect strict early-era coverage and show 2018–2019 as a separate comparator. Keep sparse years and exclusions visible. Use the 2023–2026 annual panels with actual denominators and 2026 explicitly partial. Keep pre-2015 out of the headline.
- Prepare local reviewed results with the notebook template. The later Narada reader uses the selected verified chart/table output and narrative after notebook review. Keep a fresh immutable run and separately identify any later presentation revision.

[Source reel](https://www.instagram.com/reel/Dfai3hHvMDn/)
