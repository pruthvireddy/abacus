# GC lower-band long: two-year filter selection

Study 13, protocol 1.0.0. This is a conditional path study, not realized trading performance.

## Selected rule

Require the completed outer-lower-band signal candle to close in the upper half of its own high–low range. Reapply the 10-bar cooldown after filtering; enter at the next complete five-minute bar's unadjusted open.

| Year | Rule | Accepted | Valid | Mean MAE pts | Mean MFE pts | MAE/σ | MFE/σ | Capped score | Δ vs base | 95% week interval for Δ |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2025 | Unfiltered outer-band close | 218 | 207 | 11.77 | 11.50 | 1.32 | 1.40 | +0.043 | — | — |
| 2025 | Upper-half close | 158 | 148 | 10.04 | 11.24 | 1.08 | 1.39 | +0.306 | 0.263 | [-0.02, +0.55] |
| 2026 YTD | Unfiltered outer-band close | 272 | 245 | 30.94 | 23.91 | 1.56 | 1.23 | -0.309 | — | — |
| 2026 YTD | Upper-half close | 205 | 182 | 30.31 | 25.00 | 1.46 | 1.26 | -0.179 | 0.131 | [-0.05, +0.32] |

## Interpretation

The 2025-selected rule improved the prespecified score by +0.263σ in 2025 and +0.131σ in 2026 YTD. The 2026 filtered score itself was -0.179σ, and its difference interval includes zero. This is a weak directional filter candidate, not evidence of net profitability.

The same 2026 rule has a positive score difference in 26 of 35 cooldown/horizon sensitivity cells, but those cells are correlated and longer horizons weaken. All nine primary candidate filters and full sensitivity values are saved in `tables/primary.csv` and `tables/sensitivity.csv`.

2026 was a chronological check, not a pristine holdout: the earlier study had already displayed its unfiltered outcomes. The final adjusted chart snapshot is retrospective, five-minute bars do not resolve high/low ordering, and costs and executable exits are absent.
