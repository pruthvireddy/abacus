# Adverse movement of the second same-direction candle

Run `20260906T_full_v2`. This analysis covers all seven available filename-labeled Range XV exports: ES 4/5/6, GC 6/10, and NQ 10/20.

## Definition

The reversal is the first green/red candle after the opposite run. The immediately following candle is the **second same-direction candle including the reversal**. Results condition on that candle also closing in the reversal direction. The primary adverse movement is measured from that follow-through candle's own open: open-to-low for green/long and high-to-open for red/short.

## Full-period results

| Chart | Reversals | Same-direction second candle | Conditional rate | Mean adverse ticks (95% block CI) | Median | p90 | Mean adverse price | Mean adverse gross $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ES R4 | 16,771 | 12,624 | 75.46% | 4.49 (4.42–4.57) | 3.0 | 11.0 | 1.12 | $56.16 |
| ES R5 | 11,540 | 8,689 | 75.52% | 5.42 (5.31–5.55) | 4.0 | 13.0 | 1.36 | $67.81 |
| ES R6 | 8,425 | 6,239 | 74.30% | 6.37 (6.23–6.50) | 4.0 | 16.0 | 1.59 | $79.66 |
| GC R6 | 47,019 | 35,666 | 75.91% | 5.89 (5.77–6.01) | 4.0 | 16.0 | 0.59 | $58.89 |
| GC R10 | 20,603 | 15,627 | 75.97% | 9.61 (9.40–9.83) | 6.0 | 25.0 | 0.96 | $96.07 |
| NQ R10 | 128,421 | 97,350 | 75.83% | 9.40 (9.32–9.50) | 6.0 | 25.0 | 2.35 | $47.02 |
| NQ R20 | 38,909 | 29,416 | 75.67% | 18.69 (18.44–18.93) | 12.0 | 48.0 | 4.67 | $93.45 |

The denominator for mean adverse movement is the number of same-direction second candles, not all reversals. The conditional rate column shows how frequently a reversal reached that cohort. Confidence intervals resample provisional export dates and account for within-date dependence.

## Chart-level summary

- **ES R4:** mean adverse movement was 4.49 ticks (1.12 native price units; $56.16 gross), with median 3.0 and p90 11.0 ticks. The next candle closed in the reversal direction in 75.46% of eligible reversals (12,624/16,730).
- **ES R5:** mean adverse movement was 5.42 ticks (1.36 native price units; $67.81 gross), with median 4.0 and p90 13.0 ticks. The next candle closed in the reversal direction in 75.52% of eligible reversals (8,689/11,505).
- **ES R6:** mean adverse movement was 6.37 ticks (1.59 native price units; $79.66 gross), with median 4.0 and p90 16.0 ticks. The next candle closed in the reversal direction in 74.30% of eligible reversals (6,239/8,397).
- **GC R6:** mean adverse movement was 5.89 ticks (0.59 native price units; $58.89 gross), with median 4.0 and p90 16.0 ticks. The next candle closed in the reversal direction in 75.91% of eligible reversals (35,666/46,984).
- **GC R10:** mean adverse movement was 9.61 ticks (0.96 native price units; $96.07 gross), with median 6.0 and p90 25.0 ticks. The next candle closed in the reversal direction in 75.97% of eligible reversals (15,627/20,569).
- **NQ R10:** mean adverse movement was 9.40 ticks (2.35 native price units; $47.02 gross), with median 6.0 and p90 25.0 ticks. The next candle closed in the reversal direction in 75.83% of eligible reversals (97,350/128,384).
- **NQ R20:** mean adverse movement was 18.69 ticks (4.67 native price units; $93.45 gross), with median 12.0 and p90 48.0 ticks. The next candle closed in the reversal direction in 75.67% of eligible reversals (29,416/38,874).

## Three-or-more preceding opposite candles

This sensitivity matches the example of at least three red candles followed by a green reversal, or vice versa.

| Chart | Same-direction second candles | Conditional rate | Mean adverse ticks (95% block CI) | Median | p90 |
|---|---:|---:|---:|---:|---:|
| ES R4 | 6,057 | 74.69% | 4.24 (4.15–4.34) | 3.0 | 10.0 |
| ES R5 | 4,130 | 74.01% | 5.19 (5.06–5.32) | 4.0 | 12.0 |
| ES R6 | 2,915 | 73.04% | 6.09 (5.90–6.28) | 4.0 | 15.0 |
| GC R6 | 17,441 | 74.40% | 5.62 (5.51–5.75) | 4.0 | 15.0 |
| GC R10 | 7,718 | 74.88% | 9.15 (8.93–9.37) | 6.0 | 24.0 |
| NQ R10 | 47,837 | 74.05% | 8.95 (8.84–9.06) | 6.0 | 24.0 |
| NQ R20 | 14,505 | 74.34% | 17.69 (17.40–17.99) | 12.0 | 45.0 |

The prior-run ≥3 cohort has slightly lower adverse movement than the all-reversal cohort in every chart, but the range-size ordering is unchanged.

## Reference-point sensitivity

All values below are ticks. A positive directional opening gap means the second candle opened favorably relative to the reversal close.

| Chart | Mean adverse from follow-through open | Mean adverse from reversal close | Mean directional opening gap |
|---|---:|---:|---:|
| ES R4 | 4.49 | 3.61 | 1.06 |
| ES R5 | 5.42 | 4.52 | 1.05 |
| ES R6 | 6.37 | 5.47 | 1.03 |
| GC R6 | 5.89 | 4.61 | 2.02 |
| GC R10 | 9.61 | 8.17 | 2.01 |
| NQ R10 | 9.40 | 7.81 | 2.39 |
| NQ R20 | 18.69 | 16.90 | 2.25 |

## Long versus short

| Chart | Long/green mean adverse | Short/red mean adverse |
|---|---:|---:|
| ES R4 | 4.53 | 4.46 |
| ES R5 | 5.45 | 5.40 |
| ES R6 | 6.50 | 6.24 |
| GC R6 | 5.94 | 5.83 |
| GC R10 | 9.75 | 9.47 |
| NQ R10 | 9.46 | 9.35 |
| NQ R20 | 18.67 | 18.71 |

Long/green and short/red means are close within every chart, so the combined-direction results are not being driven by only one reversal direction.

## Interpretation

Larger range settings generally allow larger adverse movement inside the second candle. The result should therefore be compared in ticks, native price, and dollars—not raw points across assets. The separate long/short table checks directional symmetry, and the prior-run table shows whether the three-opposite-candle example differs from the all-reversal cohort.

This is a conditional bar-geometry estimate. Selecting only second candles that ultimately close in the reversal direction uses their close to define the cohort; it is not a real-time entry filter and does not establish profitability. The signal-close sensitivity can differ from the own-open result because Range XV bars may open away from the reversal close.

## Outputs

- [All summary slices](tables/all_summary.csv)
- [Headline all-reversal results](tables/headline.csv)
- [Long and short results](tables/long_short.csv)
- [Prior-run sensitivity](tables/prior_run_sensitivity.csv)
- [Chronological stability](tables/chronological_stability.csv)
- [Independent real-event reconciliation](tables/manual_reconciliation.csv)
- [Methodology](methodology.md)
- [Data quality](data_quality.md)
- [Run manifest](run_manifest.json)

Figures: [mean adverse movement](figures/mean_adverse.svg), [median and p90](figures/adverse_distribution.svg), [long versus short](figures/long_short.svg), [prior-run sensitivity](figures/prior_run_sensitivity.svg), and [chronological stability](figures/chronological_stability.svg).
