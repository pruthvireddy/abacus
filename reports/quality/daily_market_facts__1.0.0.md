# Daily Facts 1.0.0 local release

The release contains one row per asset and weekday from June 28, 2021 through September 18, 2026. Calendar exclusions remain in the roster. Each window has its own completeness, opening readiness and logical availability.

## Verified coverage

| Asset | Window | Complete | Eligible | Missing minutes |
|---|---|---:|---:|---:|
| ES | globex | 1,045 | 1,303 | 531 |
| ES | overnight | 1,047 | 1,303 | 528 |
| ES | rth | 1,303 | 1,303 | 0 |
| ES | or15 | 1,303 | 1,303 | 0 |
| ES | first60 | 1,303 | 1,303 | 0 |
| ES | last60 | 1,303 | 1,303 | 0 |
| ES | globex_to_rth_end | 1,047 | 1,303 | 528 |
| NQ | globex | 1,184 | 1,303 | 263 |
| NQ | overnight | 1,185 | 1,303 | 261 |
| NQ | rth | 1,303 | 1,303 | 0 |
| NQ | or15 | 1,303 | 1,303 | 0 |
| NQ | first60 | 1,303 | 1,303 | 0 |
| NQ | last60 | 1,303 | 1,303 | 0 |
| NQ | globex_to_rth_end | 1,185 | 1,303 | 261 |
| GC | globex | 423 | 1,306 | 22,301 |
| GC | overnight | 533 | 1,306 | 14,254 |
| GC | rth | 1,272 | 1,306 | 2,874 |
| GC | or15 | 1,285 | 1,306 | 97 |
| GC | first60 | 1,280 | 1,306 | 434 |
| GC | last60 | 1,272 | 1,306 | 851 |
| GC | globex_to_rth_end | 533 | 1,306 | 17,128 |

The release contains 4,095 rows and matches all 21 audited window and prefix aggregates, including missing-minute totals. An independent retained-source comparison passed on 30 asset sessions covering exact prices, contract volumes, rational VWAP, gaps, context and availability.

Exact prices use decimal points at nine decimal places. Derived fractional and VWAP values are stored as float64 and checked with relative tolerance 1e-12 and absolute tolerance 1e-9. Logical timing uses the retained snapshots. Historical provider vintages and actual dissemination timing are unverified.

The preceding weekday supplies the opening reference when eligible and on the same contract. An excluded weekday, incomplete RTH, a roll or the pilot boundary leaves the reference empty.

The manifest inventories 61 pinned input files, output Parquet, schema, quality and the retained producer sources.

[Manifest](../../catalog/datasets/daily_market_facts__1.0.0.json) · [Schema](../../catalog/schemas/daily_market_facts__1.0.0.json) · [Frozen request](../../requests/fulfilled/daily_market_facts__1.0.0.yaml) · [Input audit](daily-facts-v1-input-audit-20261108/README.md)
